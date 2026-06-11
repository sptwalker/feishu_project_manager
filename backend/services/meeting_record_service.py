"""周会记录归档服务

把"每次周例会"做成可归档、可回溯的记录：
- 开启周会(open_meeting)：创建/更新本次记录(status=active)，开启周会模式并校准次数；
  若存在更早的未结束周会，先归档它。
- 关闭/结束(close_meeting/archive_meeting)：把当次各项目进展扫描成快照固化入库(status=archived)。
- 翻阅(get_session_detail/list_sessions)：归档快照优先，未归档的旧 session 回退动态扫描 progress_log。

会议日期、记录人在 meeting_records 表持久化（项目进展记录本身不含这些）。
聚合排序口径与前端项目总览/周会窗一致：部门简称 › 负责人 › 优先级。
"""
import logging
from datetime import date, datetime
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session

from backend.models.project import Project
from backend.models.department import Department
from backend.models.meeting_record import MeetingRecord
from backend.services.settings_service import SettingsService

logger = logging.getLogger(__name__)

# 优先级权重（与前端 urgencyWeight 一致：重要 > 高 > 中 > 低）
_URGENCY_WEIGHT = {"urgent": 4, "high": 3, "medium": 2, "low": 1}

# 进展状态 → 飞书文档字体色枚举（1红 2橙 3黄 4绿 5蓝 6紫 7灰），与前端 progressStatusColor 近似对应
_STATUS_DOC_COLOR = {
    "正常": 4, "延迟": 3, "暂停": 7, "阻塞": 1,
    "等待": 5, "待讨论": 2, "待执行": 5, "待确认": 6,
}


def _dept_map(db: Session) -> Dict[str, Dict[str, Any]]:
    """部门名 → {short, color} 映射"""
    out: Dict[str, Dict[str, Any]] = {}
    for d in db.query(Department).all():
        out[d.name] = {"short": d.short_name or d.name, "color": d.color}
    return out


class MeetingRecordService:
    """周会记录服务"""

    # ---------- 快照聚合 ----------

    @staticmethod
    def build_snapshot(db: Session, session: int) -> List[Dict[str, Any]]:
        """扫描所有项目 progress_log，聚合该次周会(meeting_session==session)的各项目最新进展。
        每项目取该次最新一条，按 部门简称 › 负责人 › 优先级(重要在前) 排序。"""
        depts = _dept_map(db)
        items: List[Dict[str, Any]] = []
        for p in db.query(Project).all():
            entries = [
                e for e in (p.progress_log or [])
                if isinstance(e, dict) and e.get("meeting_session") == session
            ]
            if not entries:
                continue
            latest = sorted(entries, key=lambda e: e.get("time", ""))[-1]
            dinfo = depts.get(p.department or "", {})
            items.append({
                "dept": p.department,
                "dept_short": dinfo.get("short") or (p.department or ""),
                "dept_color": dinfo.get("color"),
                "project": p.name,
                "owner": p.owner_name,
                "status": latest.get("status", ""),
                "content": latest.get("content", ""),
                "time": latest.get("time", ""),
                "urgency": p.urgency.value if p.urgency else "medium",
            })

        def sort_key(it: Dict[str, Any]):
            return (
                it.get("dept_short") or "",
                it.get("owner") or "",
                -_URGENCY_WEIGHT.get(it.get("urgency", "medium"), 2),
            )
        items.sort(key=sort_key)
        return items

    # ---------- 查询 ----------

    @staticmethod
    def _get_record(db: Session, session: int) -> Optional[MeetingRecord]:
        return db.query(MeetingRecord).filter(MeetingRecord.session == session).first()

    @staticmethod
    def get_session_detail(db: Session, session: int) -> Dict[str, Any]:
        """某次周会详情：归档优先（固定快照），否则动态扫描。"""
        rec = MeetingRecordService._get_record(db, session)
        if rec and rec.status == "archived" and rec.content_snapshot:
            items = rec.content_snapshot
        else:
            items = MeetingRecordService.build_snapshot(db, session)

        # 会议日期：归档表优先；否则取快照内最新一条进展的日期
        meeting_date = None
        recorder = None
        doc_url = None
        status = "archived"
        if rec:
            meeting_date = rec.meeting_date.isoformat() if rec.meeting_date else None
            recorder = rec.recorder
            doc_url = rec.doc_url
            status = rec.status
        if not meeting_date and items:
            latest_time = max((it.get("time", "") for it in items), default="")
            meeting_date = latest_time[:10] if latest_time else None

        return {
            "session": session,
            "meeting_date": meeting_date,
            "recorder": recorder,
            "status": status,
            "doc_url": doc_url,
            "items": items,
        }

    @staticmethod
    def list_sessions(db: Session) -> Dict[str, Any]:
        """所有可翻阅的周会次数（归档表 + progress_log 出现过的 + 当前周），升序。"""
        archived = {r.session for r in db.query(MeetingRecord.session).all()}
        scanned = {r["session"] for r in SettingsService.scan_meeting_records(db)}
        state = SettingsService.get_meeting_state(db)
        current = int(state["this_week_count"])
        sessions = sorted(archived | scanned | {current})
        return {"sessions": sessions, "current": current}

    # ---------- 开启 / 结束 ----------

    @staticmethod
    def archive_meeting(db: Session, session: int) -> MeetingRecord:
        """把某次周会固化为快照并置 archived。"""
        snapshot = MeetingRecordService.build_snapshot(db, session)
        rec = MeetingRecordService._get_record(db, session)
        if rec:
            rec.content_snapshot = snapshot
            rec.status = "archived"
            rec.ended_at = datetime.now()
            # 归档清空服务端计时与主控状态，下次开会从零开始
            rec.timer_state = None
            rec.controller_client_id = None
            rec.controller_heartbeat_at = None
        else:
            rec = MeetingRecord(
                session=session,
                meeting_date=date.today(),
                status="archived",
                content_snapshot=snapshot,
                ended_at=datetime.now(),
            )
            db.add(rec)
        try:
            db.commit()
            db.refresh(rec)
        except Exception:
            db.rollback()
            raise
        return rec

    @staticmethod
    def open_meeting(db: Session, session: int, recorder: Optional[str],
                     meeting_date: date, created_by: Optional[int] = None) -> Dict[str, Any]:
        """开启周会：结束其它进行中的周会 → upsert 本次(active) → 开启模式并校准次数。"""
        # 1. 结束其它进行中的旧周会
        actives = db.query(MeetingRecord).filter(
            MeetingRecord.status == "active",
            MeetingRecord.session != session,
        ).all()
        for old in actives:
            MeetingRecordService.archive_meeting(db, old.session)

        # 2. upsert 本次
        rec = MeetingRecordService._get_record(db, session)
        if rec:
            rec.meeting_date = meeting_date
            rec.recorder = recorder
            rec.status = "active"
            if created_by is not None:
                rec.created_by = created_by
        else:
            rec = MeetingRecord(
                session=session, meeting_date=meeting_date, recorder=recorder,
                status="active", content_snapshot=[], created_by=created_by,
            )
            db.add(rec)
        try:
            db.commit()
            db.refresh(rec)
        except Exception:
            db.rollback()
            raise

        # 3. 开启周会模式（次数以 meeting_records 表为真相源，不再写 base 锚点，避免双写打架）
        SettingsService.set_active(db, True)
        return MeetingRecordService.get_session_detail(db, session)

    @staticmethod
    def start_report(db: Session, session: int) -> bool:
        """记录某次周会汇报开始时刻（仅首次写入，幂等）。
        返回 True=本次为首次写入 started_at（应记一条开始日志）；
        False=已开始过 / 无该 session 记录（不应重复记日志）。"""
        rec = MeetingRecordService._get_record(db, session)
        if rec is None:
            return False
        if rec.started_at is not None:
            return False   # 已开始过，幂等：不重复写、不重复记日志
        rec.started_at = datetime.now()
        try:
            db.commit()
            db.refresh(rec)
        except Exception:
            db.rollback()
            raise
        return True

    @staticmethod
    def close_meeting(db: Session) -> None:
        """关闭周会：归档当前进行中的周会，并关闭周会模式。"""
        actives = db.query(MeetingRecord).filter(MeetingRecord.status == "active").all()
        for rec in actives:
            MeetingRecordService.archive_meeting(db, rec.session)
        SettingsService.set_active(db, False)

    # ---------- 发送到飞书 ----------

    @staticmethod
    async def send_meeting(db: Session, session: int) -> Dict[str, Any]:
        """生成飞书云文档并把链接分享到核心组群。受 FEISHU_NOTIFY_ENABLED 保护。"""
        from backend.core.config import get_settings
        from backend.core.feishu import feishu_client, FeishuAPIError
        from backend.services.notification_service import NotificationService

        settings = get_settings()
        detail = MeetingRecordService.get_session_detail(db, session)
        items = detail.get("items") or []
        if not items:
            return {"ok": False, "doc_url": None, "message": "本次周会暂无记录，无法发送"}

        if not settings.FEISHU_NOTIFY_ENABLED:
            return {"ok": False, "doc_url": None, "message": "飞书通知未开启（FEISHU_NOTIFY_ENABLED=False）"}

        meeting_date = detail.get("meeting_date") or ""
        recorder = detail.get("recorder") or ""
        title = f"第 {session} 次周会纪要"

        # 1. 组织文档块：一级标题 + 会议信息 + 按部门分组（带序号/项目数的二级标题、块间空行）
        #    项目行：项目名加粗、状态按颜色、内容换行压空格
        blocks = [feishu_client.heading_block(title, level=1)]
        head = []
        if meeting_date:
            head.append(f"会议日期：{meeting_date}")
        if recorder:
            head.append(f"记录人：{recorder}")
        if head:
            blocks.append(feishu_client.text_block(" ｜ ".join(head)))

        # 按部门分组（items 已按 部门 › 负责人 › 优先级 排序）
        groups: List[tuple] = []
        for it in items:
            dept = it.get("dept_short") or it.get("dept") or "未分组"
            if not groups or groups[-1][0] != dept:
                groups.append((dept, []))
            groups[-1][1].append(it)

        for gi, (dept, gitems) in enumerate(groups, start=1):
            if gi > 1:
                blocks.append(feishu_client.text_block(""))  # 部门块之间空行分隔
            blocks.append(feishu_client.heading_block(f"{gi}. {dept}（{len(gitems)}）", level=2))
            for it in gitems:
                status = it.get("status", "")
                content = (it.get("content") or "").replace("\n", " ").replace("\r", " ").strip()
                blocks.append(feishu_client.rich_block([
                    (it.get("project", ""), True),
                    (f" · {it.get('owner') or '—'} · ", False),
                    (f"【{status}】", False, _STATUS_DOC_COLOR.get(status)),
                    (content, False),
                ]))

        # 2. 创建飞书文档并写入
        try:
            document_id = await feishu_client.create_document(title)
            await feishu_client.append_document_blocks(document_id, blocks)
        except FeishuAPIError as e:
            logger.warning(f"创建飞书文档失败: {e}")
            return {"ok": False, "doc_url": None, "message": f"创建飞书文档失败：{e}"}

        doc_url = f"{settings.FEISHU_DOC_URL_PREFIX.rstrip('/')}/docx/{document_id}"

        # 3. 回写 doc_url
        rec = MeetingRecordService._get_record(db, session)
        if rec:
            rec.doc_url = doc_url
            try:
                db.commit()
            except Exception:
                db.rollback()

        # 4. 分享到核心组群
        # chat_id 改为从系统设置(DB)读取，所见即所得；留空则不发送
        chat_id = SettingsService.get_core_group_chat_id(db)
        sent = await NotificationService.notify_meeting_doc(
            chat_id, session, meeting_date, recorder, doc_url,
        )
        msg = "已生成飞书文档并分享到核心群" if sent else "已生成飞书文档（核心群未配置或发送失败）"
        return {"ok": True, "doc_url": doc_url, "message": msg}

