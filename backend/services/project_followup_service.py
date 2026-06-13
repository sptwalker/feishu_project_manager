"""项目进展跟催服务

定时扫描项目，找出"需要催办"的项目，组织成飞书群卡片催办相关负责人。
判定口径与前端项目总览（ProjectOverviewView.vue）保持同源一致：

- 进展停滞：最新一条 progress_log.time 距今超过阈值天数（默认 30，可在系统设置覆盖）
- 未闭合待办：progress_log 中存在 pending 状态（待讨论/待确认/待执行）、
  本身不是反馈（无 reply_to）、且其 id 未被任何 reply_to 引用的条目

负责人 → 飞书账号映射为「过渡方案」：当前项目 owner_name 是纯姓名字符串，
尝试用姓名（或英文名）反查已注册用户拿 feishu_user_id 实现 @ 个人；
查不到则退化为正文文字提负责人姓名，保证不漏发。待未来项目数据与用户账号
正式关联后，可将 resolve_owner_feishu_id 替换为直接读取关联字段。

纯查询函数（find_at_risk_projects / 各判定）不依赖飞书，便于单测。
真实外发受 FEISHU_NOTIFY_ENABLED 控制。
"""
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

from backend.models.project import Project, ProjectStatus
from backend.models.user import User
from backend.core.config import get_settings
from backend.services.settings_service import SettingsService
from backend.services.notification_service import NotificationService
from backend.services.operation_log_service import OperationLogService

logger = logging.getLogger(__name__)

# pending（未结束）进展状态，与前端 PENDING_STATUSES 同口径
PENDING_STATUSES = ("待讨论", "待确认", "待执行")

# 视为"在跟踪中"的项目状态（已完成/取消的不催办）
_TRACKED_PROJECT_STATUSES = (ProjectStatus.PLANNED, ProjectStatus.IN_PROGRESS, ProjectStatus.PAUSED)

# 系统设置键：停滞催办天数阈值（可在「系统设置 › 其他设置」修改）
SETTING_FOLLOWUP_STALL_DAYS = "followup_stall_days"
DEFAULT_FOLLOWUP_STALL_DAYS = 30


def get_stall_days_threshold(db: Session) -> int:
    """读取停滞催办天数阈值（系统设置优先，缺失/非法回退默认 30）"""
    raw = SettingsService.get_setting(db, SETTING_FOLLOWUP_STALL_DAYS, str(DEFAULT_FOLLOWUP_STALL_DAYS))
    try:
        val = int(raw)
        return val if val > 0 else DEFAULT_FOLLOWUP_STALL_DAYS
    except (TypeError, ValueError):
        return DEFAULT_FOLLOWUP_STALL_DAYS


def _latest_progress_time(project: Project) -> Optional[str]:
    """返回项目最新一条进展的 time 字符串（'YYYY-MM-DD HH:mm'），无记录返回 None"""
    log = project.progress_log or []
    times = [e.get("time", "") for e in log if isinstance(e, dict) and e.get("time")]
    if not times:
        return None
    return max(times)


def progress_stall_days(project: Project, now: Optional[datetime] = None) -> Optional[int]:
    """项目最新进展距今天数。无任何带时间的进展记录时返回 None。"""
    now = now or datetime.now()
    latest = _latest_progress_time(project)
    if not latest:
        return None
    try:
        t = datetime.fromisoformat(latest.replace(" ", "T"))
    except ValueError:
        return None
    delta = now - t
    return max(0, delta.days)


def unclosed_pending_statuses(project: Project) -> List[str]:
    """返回项目中未闭合的 pending 状态列表（去重、保持 PENDING_STATUSES 顺序）。

    未闭合：pending 状态、非反馈本身（无 reply_to）、且其 id 未被任何 reply_to 引用。
    与前端 ProjectOverviewView.vue 的 openSet 算法一致。
    """
    log = project.progress_log or []
    replied = {
        e.get("reply_to") for e in log
        if isinstance(e, dict) and e.get("reply_to")
    }
    open_set = set()
    for e in log:
        if not isinstance(e, dict):
            continue
        status = e.get("status")
        if status not in PENDING_STATUSES:
            continue
        if e.get("reply_to"):
            continue
        if e.get("id") and e.get("id") in replied:
            continue
        open_set.add(status)
    return [s for s in PENDING_STATUSES if s in open_set]


class ProjectFollowupService:
    """项目进展跟催服务"""

    # ---------- 纯查询（可独立单测） ----------

    @staticmethod
    def find_at_risk_projects(
        db: Session,
        stall_days_threshold: Optional[int] = None,
        now: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """查找需要催办的项目。

        命中任一口径即纳入：
        - 进展停滞：最新进展距今 >= 阈值天数（无进展记录的在跟踪项目也视为停滞）
        - 存在未闭合待办

        返回 [{project, owner_name, stall_days, no_progress, pending_list, reasons}]
        """
        now = now or datetime.now()
        threshold = stall_days_threshold if stall_days_threshold is not None else get_stall_days_threshold(db)

        result: List[Dict[str, Any]] = []
        projects = (
            db.query(Project)
            .filter(Project.status.in_(_TRACKED_PROJECT_STATUSES))
            .all()
        )
        for p in projects:
            stall_days = progress_stall_days(p, now)
            no_progress = stall_days is None
            pending_list = unclosed_pending_statuses(p)

            reasons: List[str] = []
            # 停滞：有进展但超阈值，或完全无进展记录
            if no_progress:
                reasons.append("无进展记录")
            elif stall_days >= threshold:
                reasons.append(f"进展停滞 {stall_days} 天")
            if pending_list:
                reasons.append("存在未闭合待办：" + "、".join(pending_list))

            if not reasons:
                continue

            result.append({
                "project": p,
                "owner_name": p.owner_name,
                "stall_days": stall_days,
                "no_progress": no_progress,
                "pending_list": pending_list,
                "reasons": reasons,
            })
        return result

    @staticmethod
    def resolve_owner_feishu_id(db: Session, owner_name: Optional[str]) -> Optional[str]:
        """过渡方案：用项目负责人姓名反查已注册用户的 feishu_user_id。

        先按中文名精确匹配，再按英文名匹配。查不到返回 None（调用方退化为文字提名）。
        未来项目与账号正式关联后，此方法可改为直接读取关联字段。
        """
        if not owner_name:
            return None
        name = owner_name.strip()
        if not name:
            return None
        user = db.query(User).filter(User.name == name).first()
        if not user:
            user = db.query(User).filter(User.name_en == name).first()
        return user.feishu_user_id if user and user.feishu_user_id else None

    # ---------- 通知编排（发到配置的项目群） ----------

    @staticmethod
    async def send_project_followups(
        db: Session,
        stall_days_threshold: Optional[int] = None,
        now: Optional[datetime] = None,
    ) -> int:
        """扫描需催办项目并发送群催办卡片。返回实际发送条数（0 或 1）。"""
        settings = get_settings()
        chat_id = settings.FEISHU_PROJECT_GROUP_CHAT_ID or None
        if not chat_id:
            logger.debug("FEISHU_PROJECT_GROUP_CHAT_ID not configured; skip project followups")
            return 0

        at_risk = ProjectFollowupService.find_at_risk_projects(db, stall_days_threshold, now)
        if not at_risk:
            logger.info("No at-risk projects to follow up")
            return 0

        # 为每个项目补充 @ 标记（解析到 feishu_id 则 @ 个人，否则文字提名）
        items: List[Dict[str, Any]] = []
        for entry in at_risk:
            feishu_id = ProjectFollowupService.resolve_owner_feishu_id(db, entry["owner_name"])
            items.append({**entry, "owner_feishu_id": feishu_id})

        ok = await NotificationService.notify_project_followups(chat_id, items)
        return 1 if ok else 0

    # ---------- 按负责人聚合 + 私聊催办（手动/自动） ----------

    @staticmethod
    def _reason_texts(entry: Dict[str, Any]) -> List[str]:
        """把一条 at-risk 项目转为催办原因文案列表（用于 DM 正文）。"""
        reasons: List[str] = []
        for st in entry.get("pending_list") or []:
            reasons.append(f"有未处理的{st}事项")
        if entry.get("no_progress"):
            reasons.append("暂无任何进展记录")
        elif entry.get("stall_days") is not None and entry["stall_days"] >= 0:
            # 仅当达到停滞阈值时 find_at_risk_projects 才会把它列为停滞原因
            if any("停滞" in r for r in (entry.get("reasons") or [])):
                reasons.append(f"超过{entry['stall_days']}天没有反馈进展信息")
        return reasons

    @staticmethod
    def group_at_risk_by_owner(
        db: Session,
        stall_days_threshold: Optional[int] = None,
        now: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """按负责人聚合需催办项目。返回每负责人：
        {owner, resolvable, stalled:[{name}], pending:[{name}],
         projects:[{name, reason}], stalled_count, pending_count}
        （projects 每项目一行、合并原因，用于 DM；stalled/pending 为两个展示维度）"""
        at_risk = ProjectFollowupService.find_at_risk_projects(db, stall_days_threshold, now)
        groups: Dict[str, Dict[str, Any]] = {}
        for entry in at_risk:
            owner = (entry.get("owner_name") or "").strip() or "未指定"
            g = groups.setdefault(owner, {
                "owner": owner, "stalled": [], "pending": [], "projects": [],
            })
            name = entry["project"].name
            is_stalled = entry.get("no_progress") or any(
                "停滞" in r for r in (entry.get("reasons") or [])
            )
            is_pending = bool(entry.get("pending_list"))
            if is_stalled:
                g["stalled"].append({"name": name})
            if is_pending:
                g["pending"].append({"name": name})
            reason = "；".join(ProjectFollowupService._reason_texts(entry)) or "需要关注"
            g["projects"].append({"name": name, "reason": reason})

        result: List[Dict[str, Any]] = []
        for owner, g in groups.items():
            feishu_id = ProjectFollowupService.resolve_owner_feishu_id(db, owner)
            result.append({
                **g,
                "resolvable": bool(feishu_id),
                "stalled_count": len(g["stalled"]),
                "pending_count": len(g["pending"]),
            })
        # 按待办+停滞总数降序，便于优先催办
        result.sort(key=lambda x: -(x["stalled_count"] + x["pending_count"]))
        return result

    @staticmethod
    async def send_owner_followup(
        db: Session,
        owner_name: str,
        *,
        auto: bool = False,
        operator: Optional[User] = None,
        now: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """向单个负责人私聊催办（实时重算其 at-risk 项目）。返回 {sent, reason?}。
        operator：手动催办的触发管理员（写日志用）；auto=True 时操作人记为系统。"""
        owner = (owner_name or "").strip()
        if not owner:
            return {"sent": False, "reason": "负责人为空"}
        groups = ProjectFollowupService.group_at_risk_by_owner(db, now=now)
        g = next((x for x in groups if x["owner"] == owner), None)
        if not g or not g["projects"]:
            return {"sent": False, "reason": "无需催办"}
        feishu_id = ProjectFollowupService.resolve_owner_feishu_id(db, owner)
        if not feishu_id:
            return {"sent": False, "reason": "未关联飞书账号"}
        ok = await NotificationService.notify_owner_followup(
            feishu_id, owner, g["projects"], auto=auto,
        )
        if ok:
            # 记录催办发送日志：手动=触发管理员，自动=系统；每催一个负责人一条
            n = len(g["projects"])
            kind = "自动催办" if auto else "手动催办"
            OperationLogService.log(
                db,
                user=None if auto else operator,
                user_name="系统" if auto else None,
                action="followup",
                target=owner,
                description=f"向{owner}发送了{kind}（{n}个项目）",
            )
        return {"sent": bool(ok), "reason": None if ok else "发送失败或通知未开启"}

    @staticmethod
    async def run_auto_followup_all(db: Session, *, auto: bool = True,
                                    operator: Optional[User] = None,
                                    now: Optional[datetime] = None) -> int:
        """遍历可解析的负责人逐个私聊催办，返回成功条数（自动定时催办用）。"""
        groups = ProjectFollowupService.group_at_risk_by_owner(db, now=now)
        sent = 0
        for g in groups:
            if not g["resolvable"]:
                continue
            res = await ProjectFollowupService.send_owner_followup(
                db, g["owner"], auto=auto, operator=operator, now=now)
            if res.get("sent"):
                sent += 1
        return sent

