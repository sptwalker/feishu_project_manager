"""留言讨论区业务服务

- 邮箱验证码：发送（60s 冷却 / 每日≤10 封；SMTP 未配置时降级打印到日志，便于本地测试）、
  校验（10 分钟有效 / 5 次错误作废）。
- 外部用户：无密码，验证码通过即注册/登录，签发独立 JWT（与内部 token 不同 secret 派生，杜绝互认）。
- 留言：楼结构（thread_id），外部发根帖/楼内补充，内部回复/星级/隐藏/封禁。
- 限流：发帖 1 条/分钟、50 条/天；单 IP 注册 ≤5 账号/天。
"""
import hashlib
import hmac
import logging
import random
import smtplib
from datetime import datetime, timedelta, timezone
from email.header import Header
from email.mime.text import MIMEText
from email.utils import formataddr
from typing import Any, Dict, List, Optional

from jose import jwt, JWTError
from sqlalchemy.orm import Session

from backend.core.config import get_settings
from backend.discuss.models import DiscussUser, DiscussCode, DiscussBoard, DiscussMessage

logger = logging.getLogger(__name__)

# 验证码参数
CODE_TTL_MINUTES = 10      # 有效期
CODE_MAX_ATTEMPTS = 5      # 最多错误次数
CODE_RESEND_SECONDS = 60   # 重发冷却
CODE_DAILY_LIMIT = 10      # 每邮箱每日上限
# 发帖限流
POST_MIN_INTERVAL_SECONDS = 60
POST_DAILY_LIMIT = 50
# 单帖附件数量上限（防刷图/刷视频）
MAX_IMAGES_PER_POST = 9
MAX_VIDEOS_PER_POST = 1
# 注册限流：单 IP 每日新账号上限。邮箱验证码（唯一邮箱 + 冷却 + 每日上限）才是主要防线；
# 此限额仅防单机批量注册，故放宽到较高值，避免共享出口/运营商 NAT 下误伤正常用户。
REGISTER_IP_DAILY_LIMIT = 30
# 内容约束
CONTENT_MAX_LEN = 2000
NICKNAME_MAX_LEN = 50


class DiscussError(Exception):
    """业务错误（message 直接给前端展示）"""
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _discuss_secret() -> str:
    """外部用户 JWT 的独立密钥：从主 SECRET_KEY 派生（HMAC），与内部 token 永不互认。"""
    return hmac.new(get_settings().SECRET_KEY.encode(), b"discuss-external-jwt", hashlib.sha256).hexdigest()


def create_ext_token(user_id: int) -> str:
    """签发外部用户 token（独立密钥 + aud 标记，30 天）。"""
    s = get_settings()
    payload = {
        "sub": str(user_id),
        "aud": "discuss",
        "exp": datetime.now(timezone.utc) + timedelta(days=s.DISCUSS_TOKEN_EXPIRE_DAYS),
    }
    return jwt.encode(payload, _discuss_secret(), algorithm="HS256")


def verify_ext_token(token: str) -> Optional[int]:
    """校验外部 token，返回用户 id；无效返回 None。"""
    try:
        payload = jwt.decode(token, _discuss_secret(), algorithms=["HS256"], audience="discuss")
        return int(payload["sub"])
    except (JWTError, KeyError, ValueError):
        return None


class DiscussService:
    """留言讨论区业务"""

    # ---------- 邮件 / 验证码 ----------

    @staticmethod
    def send_email(smtp_cfg: dict, to_addr: str, subject: str, body: str) -> bool:
        """发送邮件（布尔结果，供验证码流程用）。"""
        ok, _ = DiscussService.send_email_verbose(smtp_cfg, to_addr, subject, body)
        return ok

    @staticmethod
    def send_email_verbose(smtp_cfg: dict, to_addr: str, subject: str, body: str) -> tuple[bool, str]:
        """发送邮件，返回 (是否成功, 失败原因)。原因用于「测试邮件」直接回显给管理员定位问题。
        SMTP 未配置（host 为空）→ 降级：打印到日志并返回成功（本地测试模式）。"""
        host = (smtp_cfg.get("host") or "").strip()
        if not host:
            logger.warning("[discuss] SMTP 未配置，邮件降级打印 → to=%s subject=%s body=%s",
                           to_addr, subject, body)
            return True, "SMTP 未配置（已降级打印到日志）"
        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = Header(subject, "utf-8")
        username = (smtp_cfg.get("username") or "").strip()
        from_field = (smtp_cfg.get("sender") or "").strip()
        # 发件地址：发件人填了完整邮箱才用它，否则回退登录账号
        # （发件人填的是名字/留空时不当地址用，避免出现非法地址）。
        from_addr = from_field if "@" in from_field else username
        # 信封 MAIL FROM 必须是有效邮箱，且多数服务商（如阿里企业邮）要求与登录账号一致：
        # 恒用登录账号，杜绝把「发件人显示名」误当信封地址导致 500 bad syntax。
        envelope_from = username or from_addr
        msg["From"] = formataddr((str(Header("留言讨论区", "utf-8")), from_addr))
        msg["To"] = to_addr
        try:
            port = int(smtp_cfg.get("port") or 465)
            # 传输方式按端口推导（对齐经验证可用的做法，避免 SSL 勾选与端口配错）：
            # 465 = 隐式 SSL（强制）；其余端口 = 明文 + STARTTLS（ssl 勾选时启用，默认启用）。
            if port == 465:
                server = smtplib.SMTP_SSL(host, port, timeout=10)
            else:
                server = smtplib.SMTP(host, port, timeout=10)
                if smtp_cfg.get("ssl", True):
                    server.starttls()
            with server:
                if username:
                    server.login(username, smtp_cfg.get("password") or "")
                server.sendmail(envelope_from, [to_addr], msg.as_string())
            return True, ""
        except Exception as e:  # noqa: BLE001 - 邮件失败要转成用户可读错误
            logger.warning("[discuss] 发送邮件失败: %s", e)
            return False, f"{type(e).__name__}: {e}"

    @staticmethod
    def request_code(db: Session, email: str, smtp_cfg: dict) -> None:
        """发送验证码：60s 冷却、每日 ≤10 封；同邮箱重发覆盖旧码。"""
        email = email.strip().lower()
        if "@" not in email or len(email) > 200:
            raise DiscussError("邮箱格式不正确")
        now = datetime.now()
        today = now.strftime("%Y-%m-%d")
        rec = db.query(DiscussCode).filter(DiscussCode.email == email).first()
        if rec:
            if (now - rec.sent_at).total_seconds() < CODE_RESEND_SECONDS:
                raise DiscussError("发送过于频繁，请稍后再试", 429)
            daily = rec.daily_count if rec.daily_date == today else 0
            if daily >= CODE_DAILY_LIMIT:
                raise DiscussError("今日验证码发送次数已达上限", 429)
        code = f"{random.randint(0, 999999):06d}"
        if rec:
            rec.code_hash = _hash(code)
            rec.expires_at = now + timedelta(minutes=CODE_TTL_MINUTES)
            rec.attempts = 0
            rec.sent_at = now
            rec.daily_count = (rec.daily_count + 1) if rec.daily_date == today else 1
            rec.daily_date = today
        else:
            db.add(DiscussCode(
                email=email, code_hash=_hash(code),
                expires_at=now + timedelta(minutes=CODE_TTL_MINUTES),
                attempts=0, sent_at=now, daily_count=1, daily_date=today,
            ))
        db.commit()
        ok = DiscussService.send_email(
            smtp_cfg, email, "留言区验证码",
            f"您的验证码是：{code}（{CODE_TTL_MINUTES} 分钟内有效）。若非本人操作请忽略。",
        )
        if not ok:
            raise DiscussError("邮件发送失败，请稍后再试或联系管理员", 502)

    @staticmethod
    def _consume_code(db: Session, email: str, code: str) -> None:
        """校验并消费验证码（一次性；错误累计 5 次作废）。"""
        rec = db.query(DiscussCode).filter(DiscussCode.email == email).first()
        if rec is None:
            raise DiscussError("请先获取验证码")
        now = datetime.now()
        if now > rec.expires_at or rec.attempts >= CODE_MAX_ATTEMPTS:
            raise DiscussError("验证码已失效，请重新获取")
        if rec.code_hash != _hash(code.strip()):
            rec.attempts += 1
            db.commit()
            raise DiscussError("验证码错误")
        db.delete(rec)   # 验证通过即消费
        db.commit()

    # ---------- 注册 / 登录 ----------

    @staticmethod
    def register(db: Session, email: str, code: str, nickname: str, phone: str,
                 client_ip: str) -> DiscussUser:
        """注册：验证码通过 + 昵称/手机号必填；单 IP 每日 ≤5 个新账号。"""
        email = email.strip().lower()
        nickname = (nickname or "").strip()
        phone = (phone or "").strip()
        if not nickname or len(nickname) > NICKNAME_MAX_LEN:
            raise DiscussError(f"昵称必填且不超过 {NICKNAME_MAX_LEN} 字")
        if not phone or len(phone) > 30:
            raise DiscussError("手机号必填")
        if db.query(DiscussUser).filter(DiscussUser.email == email).first():
            raise DiscussError("该邮箱已注册，请直接登录")
        ip_h = _hash(client_ip or "")
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        ip_today = db.query(DiscussUser).filter(
            DiscussUser.ip_hash == ip_h, DiscussUser.created_at >= today_start,
        ).count()
        if ip_today >= REGISTER_IP_DAILY_LIMIT:
            raise DiscussError("注册过于频繁，请明天再试", 429)
        DiscussService._consume_code(db, email, code)
        user = DiscussUser(email=email, phone=phone, nickname=nickname,
                           ip_hash=ip_h, last_seen_at=datetime.now())
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def login(db: Session, email: str, code: str) -> DiscussUser:
        """登录：验证码通过即登录（无密码）。"""
        email = email.strip().lower()
        user = db.query(DiscussUser).filter(DiscussUser.email == email).first()
        if user is None:
            raise DiscussError("该邮箱未注册，请先注册")
        if user.status == "blocked":
            raise DiscussError("该账号已被限制使用", 403)
        DiscussService._consume_code(db, email, code)
        user.last_seen_at = datetime.now()
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def get_user(db: Session, user_id: int) -> Optional[DiscussUser]:
        return db.query(DiscussUser).filter(DiscussUser.id == user_id).first()

    # ---------- 讨论区 / 留言 ----------

    @staticmethod
    def get_or_create_board(db: Session) -> DiscussBoard:
        """v1 单讨论区：取第一条，无则自动创建。"""
        board = db.query(DiscussBoard).order_by(DiscussBoard.id).first()
        if board is None:
            board = DiscussBoard(title="用户留言区", welcome_text="欢迎留言，我们会尽快回复。")
            db.add(board)
            db.commit()
            db.refresh(board)
        return board

    @staticmethod
    def post_message(db: Session, user: DiscussUser, content: str,
                     attachments: Optional[List[dict]] = None,
                     thread_id: Optional[int] = None) -> DiscussMessage:
        """外部用户发留言（thread_id=None 开新楼；否则限在自己楼内补充）。"""
        if user.status == "blocked":
            raise DiscussError("该账号已被限制使用", 403)
        content = (content or "").strip()
        if not content:
            raise DiscussError("留言内容不能为空")
        if len(content) > CONTENT_MAX_LEN:
            raise DiscussError(f"留言不能超过 {CONTENT_MAX_LEN} 字")
        # 附件数量按类型限额（防刷图/刷视频）
        atts = attachments or []
        n_img = sum(1 for a in atts if isinstance(a, dict) and a.get("type") == "image")
        n_vid = sum(1 for a in atts if isinstance(a, dict) and a.get("type") == "video")
        if n_img > MAX_IMAGES_PER_POST:
            raise DiscussError(f"每条留言最多 {MAX_IMAGES_PER_POST} 张图片")
        if n_vid > MAX_VIDEOS_PER_POST:
            raise DiscussError(f"每条留言最多 {MAX_VIDEOS_PER_POST} 个视频")
        now = datetime.now()
        # 限流：1 条/分钟、50 条/天
        last = db.query(DiscussMessage).filter(
            DiscussMessage.ext_user_id == user.id,
        ).order_by(DiscussMessage.created_at.desc()).first()
        if last and (now - last.created_at).total_seconds() < POST_MIN_INTERVAL_SECONDS:
            raise DiscussError("发布过于频繁，请稍后再试", 429)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_n = db.query(DiscussMessage).filter(
            DiscussMessage.ext_user_id == user.id, DiscussMessage.created_at >= today_start,
        ).count()
        if today_n >= POST_DAILY_LIMIT:
            raise DiscussError("今日发布次数已达上限", 429)

        board = DiscussService.get_or_create_board(db)
        if board.status != "open":
            raise DiscussError("留言区暂未开放", 403)

        parent_id = None
        if thread_id is not None:
            root = db.query(DiscussMessage).filter(DiscussMessage.id == thread_id).first()
            if root is None or root.parent_id is not None:
                raise DiscussError("楼层不存在")
            if root.ext_user_id != user.id:
                raise DiscussError("只能在自己的留言下补充", 403)
            parent_id = thread_id

        msg = DiscussMessage(
            board_id=board.id, parent_id=parent_id,
            author_type="external", ext_user_id=user.id, author_name=user.nickname,
            content=content, attachments=attachments or [],
            created_at=now,
        )
        db.add(msg)
        db.commit()
        db.refresh(msg)
        # 根留言 thread_id 自指；楼内补充继承
        msg.thread_id = msg.id if parent_id is None else thread_id
        db.commit()
        db.refresh(msg)
        user.last_seen_at = now
        db.commit()
        return msg

    @staticmethod
    def internal_reply(db: Session, thread_id: int, author_name: str, content: str) -> DiscussMessage:
        """内部用户回复某楼（标记该楼 replied=1）。"""
        content = (content or "").strip()
        if not content:
            raise DiscussError("回复内容不能为空")
        if len(content) > CONTENT_MAX_LEN:
            raise DiscussError(f"回复不能超过 {CONTENT_MAX_LEN} 字")
        root = db.query(DiscussMessage).filter(
            DiscussMessage.id == thread_id, DiscussMessage.parent_id.is_(None),
        ).first()
        if root is None:
            raise DiscussError("楼层不存在", 404)
        msg = DiscussMessage(
            board_id=root.board_id, thread_id=thread_id, parent_id=thread_id,
            author_type="internal", author_name=author_name,
            content=content, attachments=[],
        )
        db.add(msg)
        root.replied = 1
        db.commit()
        db.refresh(msg)
        return msg

    @staticmethod
    def set_star(db: Session, message_id: int, star: int) -> DiscussMessage:
        """内部评定奖励星级（0-5；0=取消）。仅根留言可评。"""
        if star < 0 or star > 5:
            raise DiscussError("星级须在 0-5 之间")
        msg = db.query(DiscussMessage).filter(
            DiscussMessage.id == message_id, DiscussMessage.parent_id.is_(None),
        ).first()
        if msg is None:
            raise DiscussError("留言不存在", 404)
        msg.star = star
        db.commit()
        db.refresh(msg)
        return msg

    @staticmethod
    def set_visibility(db: Session, message_id: int, visible: bool) -> DiscussMessage:
        """内部隐藏 / 恢复留言（先发后审的事后管控）。"""
        msg = db.query(DiscussMessage).filter(DiscussMessage.id == message_id).first()
        if msg is None:
            raise DiscussError("留言不存在", 404)
        msg.status = "visible" if visible else "hidden"
        db.commit()
        db.refresh(msg)
        return msg

    @staticmethod
    def set_user_blocked(db: Session, ext_user_id: int, blocked: bool) -> DiscussUser:
        """封禁 / 解封外部用户。"""
        user = db.query(DiscussUser).filter(DiscussUser.id == ext_user_id).first()
        if user is None:
            raise DiscussError("用户不存在", 404)
        user.status = "blocked" if blocked else "active"
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def delete_thread(db: Session, thread_id: int) -> list[dict]:
        """删除整楼（根留言 + 全部回复）。返回被删消息的附件列表，供上层清理媒体文件。"""
        root = db.query(DiscussMessage).filter(
            DiscussMessage.id == thread_id, DiscussMessage.parent_id.is_(None),
        ).first()
        if root is None:
            raise DiscussError("楼层不存在", 404)
        msgs = db.query(DiscussMessage).filter(DiscussMessage.thread_id == root.id).all()
        attachments = [
            a for m in msgs for a in (m.attachments or [])
            if isinstance(a, dict) and a.get("url")
        ]
        for m in msgs:
            db.delete(m)
        try:
            db.commit()
        except Exception:
            db.rollback()
            raise
        return attachments

    # ---------- 查询 ----------

    @staticmethod
    def _msg_public(m: DiscussMessage) -> Dict[str, Any]:
        """留言的公开视图（绝不含邮箱/手机号/内部 id）。"""
        return {
            "id": m.id, "thread_id": m.thread_id, "parent_id": m.parent_id,
            "author_type": m.author_type, "author_name": m.author_name,
            "content": m.content, "attachments": m.attachments or [],
            "star": m.star, "created_at": m.created_at.isoformat(sep=" ", timespec="minutes"),
        }

    @staticmethod
    def list_threads(db: Session, page: int = 1, size: int = 10,
                     include_hidden: bool = False,
                     only_unreplied: bool = False,
                     keyword: str = "",
                     min_star: int = 0,
                     ext_user_id: Optional[int] = None) -> Dict[str, Any]:
        """楼列表（根留言分页倒序）+ 每楼全部回复。
        公开端 include_hidden=False 且传 ext_user_id：只返回该用户自己的楼（含官方回复），
        看不到其他用户的内容；内部端可含隐藏、筛未回复、搜索、按星级过滤。"""
        q = db.query(DiscussMessage).filter(DiscussMessage.parent_id.is_(None))
        if not include_hidden:
            q = q.filter(DiscussMessage.status == "visible")
        if ext_user_id is not None:
            # 只看自己发的楼（官方对该楼的回复因 thread_id 归属仍会带出）
            q = q.filter(DiscussMessage.ext_user_id == ext_user_id)
        if only_unreplied:
            q = q.filter(DiscussMessage.replied == 0)
        if min_star > 0:
            q = q.filter(DiscussMessage.star >= min_star)
        if keyword.strip():
            kw = f"%{keyword.strip()}%"
            # 搜索：内容 / 昵称；内部端另可按邮箱/手机匹配用户后过滤
            match_users = db.query(DiscussUser.id).filter(
                (DiscussUser.email.like(kw)) | (DiscussUser.phone.like(kw)),
            ).all() if include_hidden else []
            uid_list = [u.id for u in match_users]
            cond = DiscussMessage.content.like(kw) | DiscussMessage.author_name.like(kw)
            if uid_list:
                cond = cond | DiscussMessage.ext_user_id.in_(uid_list)
            q = q.filter(cond)
        total = q.count()
        roots = q.order_by(DiscussMessage.created_at.desc()) \
                 .offset((page - 1) * size).limit(size).all()
        # 取各楼回复
        items = []
        for root in roots:
            rq = db.query(DiscussMessage).filter(
                DiscussMessage.thread_id == root.id, DiscussMessage.id != root.id,
            )
            if not include_hidden:
                rq = rq.filter(DiscussMessage.status == "visible")
            replies = rq.order_by(DiscussMessage.created_at.asc()).all()
            entry = DiscussService._msg_public(root)
            entry["replies"] = [DiscussService._msg_public(r) for r in replies]
            if include_hidden:
                # 内部端补充管理字段
                entry["status"] = root.status
                entry["replied"] = bool(root.replied)
                entry["ext_user_id"] = root.ext_user_id
                u = DiscussService.get_user(db, root.ext_user_id) if root.ext_user_id else None
                entry["ext_email"] = u.email if u else None
                entry["ext_phone"] = u.phone if u else None
                entry["ext_blocked"] = (u.status == "blocked") if u else False
                for i, r in enumerate(replies):
                    entry["replies"][i]["status"] = r.status
            items.append(entry)
        return {"total": total, "page": page, "size": size, "items": items}
