"""内部销售码服务：批量生成、逐条/批量核销、查询，以及生成用二级密码。

随机码用 secrets（密码学随机），字母表去除易混字符（0/O/1/I/L）。
二级密码用 stdlib pbkdf2_hmac 加盐哈希存 SystemSetting；未设置时以初值 888888 校验。
（不走 passlib：本机 bcrypt 5.0 与 passlib 1.7.4 不兼容；pbkdf2 为 stdlib，对这道 PIN 级二级密码足够。）
"""
from datetime import datetime
from typing import Optional
import hashlib
import secrets

from sqlalchemy.orm import Session

from backend.models.sales_code import SalesCode
from backend.models.user import User
from backend.services.settings_service import SettingsService

# 二级密码：存 pbkdf2 盐+哈希；未设置过则以初值校验
SALES_CODE_PWD_KEY = "sales_code_gen_password_hash"
DEFAULT_GEN_PASSWORD = "888888"
_PBKDF2_ROUNDS = 100_000

# 去除易混字符（无 0 O 1 I L），码形如 SC-XXXXXXXX
_ALPHABET = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"
_CODE_LEN = 8
MAX_BATCH = 1000


def _gen_code() -> str:
    return "SC-" + "".join(secrets.choice(_ALPHABET) for _ in range(_CODE_LEN))


def _hash_pwd(pwd: str) -> str:
    """pbkdf2-sha256 加随机盐，返回 "salt_hex$dk_hex"。"""
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", pwd.encode("utf-8"), salt, _PBKDF2_ROUNDS)
    return f"{salt.hex()}${dk.hex()}"


def _verify_pwd(pwd: str, stored: str) -> bool:
    """常量时间比对 pbkdf2 哈希；stored 格式非法则判否。"""
    try:
        salt_hex, dk_hex = stored.split("$", 1)
        salt = bytes.fromhex(salt_hex)
    except (ValueError, TypeError):
        return False
    dk = hashlib.pbkdf2_hmac("sha256", (pwd or "").encode("utf-8"), salt, _PBKDF2_ROUNDS)
    return secrets.compare_digest(dk.hex(), dk_hex)


class SalesCodeService:
    """内部销售码服务"""

    @staticmethod
    def generate_batch(db: Session, count: int, issued_to: str, generator: Optional[User]) -> list[SalesCode]:
        """批量生成 count 个唯一随机码并入库。批内去重 + 库内去重（碰撞重取）。"""
        if count < 1 or count > MAX_BATCH:
            raise ValueError(f"生成数量需在 1~{MAX_BATCH} 之间")
        issued_to = (issued_to or "").strip()

        codes: set[str] = set()
        while len(codes) < count:
            batch = {_gen_code() for _ in range(count - len(codes))} - codes
            if batch:
                existing = {
                    c for (c,) in db.query(SalesCode.code)
                    .filter(SalesCode.code.in_(list(batch))).all()
                }
                batch -= existing
            codes |= batch

        rows = [
            SalesCode(
                code=c, issued_to=issued_to,
                generated_by=generator.name if generator else "",
                generated_by_id=generator.id if generator else None,
                redeemed=False,
            )
            for c in codes
        ]
        db.add_all(rows)
        try:
            db.commit()
        except Exception:
            db.rollback()
            raise
        for r in rows:
            db.refresh(r)
        return sorted(rows, key=lambda r: r.code)

    @staticmethod
    def _apply_redeem(db: Session, code: str, redeemer: Optional[User]) -> tuple[bool, str, Optional[SalesCode]]:
        """核销一条（不提交）。返回 (是否成功, 原因, 记录)。"""
        code = (code or "").strip()
        if not code:
            return False, "销售码不能为空", None
        rec = db.query(SalesCode).filter(SalesCode.code == code).first()
        if not rec:
            return False, "销售码不存在", None
        if rec.redeemed:
            when = rec.redeemed_at.strftime("%Y-%m-%d %H:%M") if rec.redeemed_at else "此前"
            return False, f"已于 {when} 被 {rec.redeemed_by or '他人'} 核销", rec
        rec.redeemed = True
        rec.redeemed_at = datetime.now()
        rec.redeemed_by = redeemer.name if redeemer else ""
        return True, "核销成功", rec

    @staticmethod
    def redeem_one(db: Session, code: str, redeemer: Optional[User]) -> tuple[bool, str, Optional[SalesCode]]:
        """逐条核销：查询成功即标记核销，否则返回失败原因。"""
        ok, reason, rec = SalesCodeService._apply_redeem(db, code, redeemer)
        try:
            db.commit()
        except Exception:
            db.rollback()
            raise
        if rec is not None:
            db.refresh(rec)
        return ok, reason, rec

    @staticmethod
    def redeem_batch(db: Session, codes: list[str], redeemer: Optional[User]) -> dict:
        """批量核销：核销所有可核销的码；失败的收集原因。批内重复码只处理一次。"""
        seen: set[str] = set()
        redeemed: list[SalesCode] = []
        failed: list[dict] = []
        for raw in codes or []:
            c = (raw or "").strip()
            if not c or c in seen:
                continue
            seen.add(c)
            ok, reason, rec = SalesCodeService._apply_redeem(db, c, redeemer)
            if ok and rec is not None:
                redeemed.append(rec)
            else:
                failed.append({"code": c, "reason": reason})
        try:
            db.commit()
        except Exception:
            db.rollback()
            raise
        for r in redeemed:
            db.refresh(r)
        return {"redeemed": redeemed, "failed": failed}

    @staticmethod
    def query(
        db: Session,
        code: Optional[str] = None,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        redeemed: Optional[bool] = None,
        limit: int = 1000,
    ) -> list[SalesCode]:
        """按销售码（模糊）/ 生成时间区间 / 核销状态查询，按生成时间倒序。"""
        q = db.query(SalesCode)
        if code and code.strip():
            q = q.filter(SalesCode.code.ilike(f"%{code.strip()}%"))
        if start is not None:
            q = q.filter(SalesCode.created_at >= start)
        if end is not None:
            q = q.filter(SalesCode.created_at <= end)
        if redeemed is not None:
            q = q.filter(SalesCode.redeemed == redeemed)
        return q.order_by(SalesCode.created_at.desc(), SalesCode.id.desc()).limit(limit).all()

    # ---------- 生成用二级密码 ----------

    @staticmethod
    def verify_gen_password(db: Session, pwd: str) -> bool:
        """校验二级密码。未设置过则以初值 888888 校验；已设置则比对哈希。"""
        h = SettingsService.get_setting(db, SALES_CODE_PWD_KEY, "") or ""
        if not h:
            return (pwd or "") == DEFAULT_GEN_PASSWORD
        return _verify_pwd(pwd or "", h)

    @staticmethod
    def set_gen_password(db: Session, new_pwd: str) -> None:
        """设置新的二级密码（存哈希）。管理员已鉴权，改密不要求旧密码。"""
        new_pwd = (new_pwd or "").strip()
        if not new_pwd:
            raise ValueError("密码不能为空")
        SettingsService.set_setting(db, SALES_CODE_PWD_KEY, _hash_pwd(new_pwd))

    @staticmethod
    def is_gen_password_default(db: Session) -> bool:
        """二级密码是否仍为初始值（从未修改过）。"""
        return not (SettingsService.get_setting(db, SALES_CODE_PWD_KEY, "") or "")
