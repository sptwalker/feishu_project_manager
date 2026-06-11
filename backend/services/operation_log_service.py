"""系统操作日志服务

记录用户登录与项目操作（仅向前记录），供管理员按时间范围查询。
log() 独立吞异常——记日志失败绝不影响主业务操作。
classify_progress_change() 通过 diff 旧/新 progress_log 区分 进展更新/评论/反馈。
"""
import logging
from datetime import datetime
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session

from backend.models.operation_log import OperationLog
from backend.models.user import User

logger = logging.getLogger(__name__)


class OperationLogService:
    """系统操作日志服务"""

    @staticmethod
    def log(
        db: Session,
        *,
        user: Optional[User] = None,
        user_name: Optional[str] = None,
        action: str,
        description: str,
        target: Optional[str] = None,
        project_id: Optional[int] = None,
        occurred_at: Optional[datetime] = None,
    ) -> None:
        """写一条操作日志。独立 try/except，失败仅告警不抛出（不影响主操作）。

        user 优先取其 name 作为快照；也可直接传 user_name。
        project_id 关联项目（用于项目历史查询；不级联删除）。
        """
        try:
            name = user_name if user_name is not None else (user.name if user else "")
            row = OperationLog(
                user_id=user.id if user else None,
                project_id=project_id,
                user_name=name or "",
                action=action,
                target=target,
                description=description,
                occurred_at=occurred_at or datetime.now(),
            )
            db.add(row)
            db.commit()
        except Exception as e:  # noqa: BLE001 - 日志失败不应影响主流程
            logger.warning("写操作日志失败: %s", e)
            try:
                db.rollback()
            except Exception:
                pass

    @staticmethod
    def query(
        db: Session,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        limit: int = 1000,
        project_id: Optional[int] = None,
    ) -> List[OperationLog]:
        """查询操作日志，按发生时间倒序，限量返回。可按时间范围与项目过滤。"""
        q = db.query(OperationLog)
        if project_id is not None:
            q = q.filter(OperationLog.project_id == project_id)
        if start is not None:
            q = q.filter(OperationLog.occurred_at >= start)
        if end is not None:
            q = q.filter(OperationLog.occurred_at <= end)
        return q.order_by(OperationLog.occurred_at.desc()).limit(limit).all()

    @staticmethod
    def classify_progress_change(
        old_log: Optional[list],
        new_log: Optional[list],
    ) -> Tuple[Optional[str], Optional[str]]:
        """diff 旧/新 progress_log，判定单一动作。返回 (action, status|None)。

        优先级：
        1. 新增带 reply_to 的条目 → ("feedback", 该条目 status)
        2. 新增不带 reply_to 的条目 → ("update_progress", None)
        3. 某条目 annotations 数 或 其下 replies 数 增加 → ("comment", None)
        4. 删除了已有条目 → ("delete_progress", None)
        5. 否则 → (None, None)
        """
        old = old_log or []
        new = new_log or []

        def entry_id(e: dict) -> Optional[str]:
            return e.get("id") if isinstance(e, dict) else None

        old_ids = {entry_id(e) for e in old if entry_id(e)}
        # 1 & 2：检测新增条目
        new_entries = [e for e in new if isinstance(e, dict) and entry_id(e) and entry_id(e) not in old_ids]
        # 也兼容无 id 的情况：按数量增长判断
        if not new_entries and len(new) > len(old):
            new_entries = [e for e in new[len(old):] if isinstance(e, dict)]
        for e in new_entries:
            if e.get("reply_to"):
                # 反馈对象是「待处理事项」，其状态可能在本次保存中已流转为「已X」；
                # 取 old_log 里被反馈原事项的原状态（待X）作日志文案，避免记成「反馈了已讨论事项」
                origin = next((o for o in old if entry_id(o) == e.get("reply_to")), None)
                st = (origin.get("status") if isinstance(origin, dict) else None) or e.get("status") or ""
                return "feedback", st
        if new_entries:
            return "update_progress", None

        # 3：批注/回复数量增加
        old_by_id = {entry_id(e): e for e in old if entry_id(e)}
        for e in new:
            if not isinstance(e, dict):
                continue
            eid = entry_id(e)
            oe = old_by_id.get(eid, {})
            new_anns = e.get("annotations") or []
            old_anns = oe.get("annotations") or []
            if len(new_anns) > len(old_anns):
                return "comment", None
            # 同条批注下回复增加
            old_ann_by_id = {a.get("id"): a for a in old_anns if isinstance(a, dict) and a.get("id")}
            for a in new_anns:
                if not isinstance(a, dict):
                    continue
                oa = old_ann_by_id.get(a.get("id"), {})
                if len(a.get("replies") or []) > len(oa.get("replies") or []):
                    return "comment", None

        # 4：删除了已有条目（按 id 判断有条目消失，或无 id 时数量减少）
        new_ids = {entry_id(e) for e in new if entry_id(e)}
        removed_by_id = [eid for eid in old_ids if eid not in new_ids]
        if removed_by_id or len(new) < len(old):
            return "delete_progress", None

        return None, None
