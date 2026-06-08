"""会议计时 + 主控服务（服务端权威，客户端本地推算）

核心思想：计时是连续量，但状态转移是离散的。服务端只存少量"时间锚点"
（开始/暂停/切换汇报人的时刻 + 累计基准），客户端用 now-锚点 本地每秒推算显示。
服务端写极少（仅控制动作 + 心跳），天然多端一致、刷新不丢、SQLite/多worker 友好。

主控机制：
- 首个进入汇报页的管理员认领主控（controller_client_id），其余为协助态。
- 仅主控可改计时（control/heartbeat 校验 client_id）。
- 掉线判定与释放均为惰性：任意客户端读状态时顺带检测，无需后台任务。
  - 心跳中断 > T1(15s) 且运行中 → 自动暂停，结算时刻用「最后心跳+T1」（不计无人追踪的流逝）。
  - 心跳中断 > T2(180s) → 释放主控（置 null），协助端可接管。
  - 原主控 3min 内重连（同 client_id 心跳）→ 自动继续。
"""
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from backend.models.meeting_record import MeetingRecord
from backend.services.settings_service import SettingsService

# 两个超时阈值
OFFLINE_SECONDS = 15      # T1：心跳中断超此判为掉线并自动暂停
RELEASE_SECONDS = 180     # T2：心跳中断超此释放主控，允许协助端接管


class NoActiveMeeting(Exception):
    """当前没有进行中的周会"""


class NotController(Exception):
    """非主控客户端尝试控制计时"""


class ControllerPresent(Exception):
    """接管失败：主控仍在线/未释放"""


class VersionConflict(Exception):
    """认领/接管 CAS 版本冲突（同时有人抢主控）"""


def _now() -> datetime:
    return datetime.now()


def _parse(s: Optional[str]) -> Optional[datetime]:
    return datetime.fromisoformat(s) if s else None


def _default_state() -> Dict[str, Any]:
    return {
        "status": "idle",                 # idle | running | paused
        "total_base": 0,                  # 暂停前累计的会议总秒数
        "total_started_at": None,         # 本运行段起点（running 时有效）
        "current_presenter_key": None,    # 当前汇报人 "部门|个人"
        "segment_started_at": None,       # 当前汇报人本段起点
        "person_base": {},                # 各汇报人累计秒
        "paused_reason": None,            # null | manual | controller_offline
    }


def _ts(rec: MeetingRecord) -> Dict[str, Any]:
    """取 timer_state 的可变副本（带默认值兜底）"""
    base = _default_state()
    if rec.timer_state:
        base.update(rec.timer_state)
        # person_base 深拷贝，避免改到原引用
        base["person_base"] = dict(rec.timer_state.get("person_base") or {})
    return base


def _save_ts(rec: MeetingRecord, ts: Dict[str, Any]) -> None:
    rec.timer_state = ts
    flag_modified(rec, "timer_state")


def _settle(ts: Dict[str, Any], at: datetime) -> None:
    """把运行中的累计结算到 at 时刻（总时长 + 当前汇报人），并清空运行锚点。"""
    if ts["status"] != "running":
        return
    started = _parse(ts.get("total_started_at"))
    if started:
        ts["total_base"] = int(ts["total_base"]) + max(0, int((at - started).total_seconds()))
        ts["total_started_at"] = None
    key = ts.get("current_presenter_key")
    seg = _parse(ts.get("segment_started_at"))
    if key and seg:
        ts["person_base"][key] = int(ts["person_base"].get(key, 0)) + max(0, int((at - seg).total_seconds()))
        ts["segment_started_at"] = None


def _resume(ts: Dict[str, Any], at: datetime) -> None:
    """从暂停/idle 恢复运行：重设运行锚点。"""
    ts["status"] = "running"
    ts["paused_reason"] = None
    ts["total_started_at"] = at.isoformat()
    if ts.get("current_presenter_key"):
        ts["segment_started_at"] = at.isoformat()


class MeetingTimerService:
    """会议计时 + 主控状态机"""

    # ---------- 内部 ----------

    @staticmethod
    def _active(db: Session) -> MeetingRecord:
        rec = SettingsService.get_active_meeting_record(db)
        if rec is None:
            raise NoActiveMeeting()
        return rec

    @staticmethod
    def _apply_lazy_timeouts(db: Session, rec: MeetingRecord, now: datetime) -> bool:
        """惰性判定主控掉线/释放（任意读状态时调用）。返回是否有变更。"""
        if rec.controller_client_id is None or rec.controller_heartbeat_at is None:
            return False
        gap = (now - rec.controller_heartbeat_at).total_seconds()
        changed = False
        # T1：自动暂停（结算到「最后心跳 + T1」，掉线后流逝不计入）
        if gap > OFFLINE_SECONDS:
            ts = _ts(rec)
            if ts["status"] == "running":
                settle_at = rec.controller_heartbeat_at + timedelta(seconds=OFFLINE_SECONDS)
                _settle(ts, settle_at)
                ts["status"] = "paused"
                ts["paused_reason"] = "controller_offline"
                _save_ts(rec, ts)
                changed = True
        # T2：释放主控
        if gap > RELEASE_SECONDS:
            rec.controller_client_id = None
            rec.controller_heartbeat_at = None
            changed = True
        if changed:
            db.commit()
            db.refresh(rec)
        return changed

    @staticmethod
    def _build_state(rec: MeetingRecord, client_id: Optional[str], now: datetime) -> Dict[str, Any]:
        ts = _ts(rec)
        controller = rec.controller_client_id
        online = False
        if controller is not None and rec.controller_heartbeat_at is not None:
            online = (now - rec.controller_heartbeat_at).total_seconds() <= OFFLINE_SECONDS
        if client_id and client_id == controller:
            role = "controller"
        else:
            role = "assistant"
        return {
            "active": True,
            "session": rec.session,
            "server_now": now.isoformat(),
            "status": ts["status"],
            "total_base": int(ts["total_base"]),
            "total_started_at": ts.get("total_started_at"),
            "current_presenter_key": ts.get("current_presenter_key"),
            "segment_started_at": ts.get("segment_started_at"),
            "person_base": ts.get("person_base") or {},
            "paused_reason": ts.get("paused_reason"),
            "controller_present": controller is not None,
            "controller_online": online,
            "controller_version": int(rec.controller_version or 0),
            "my_role": role,
            "offline_seconds": OFFLINE_SECONDS,
            "release_seconds": RELEASE_SECONDS,
        }

    @staticmethod
    def _inactive_state(now: datetime) -> Dict[str, Any]:
        return {"active": False, "server_now": now.isoformat(), "my_role": "none"}

    # ---------- 对外 ----------

    @staticmethod
    def get_state(db: Session, client_id: Optional[str]) -> Dict[str, Any]:
        """读计时状态（含惰性掉线/释放判定 + server_now 供时钟校正）。无会议返回 inactive。"""
        now = _now()
        rec = SettingsService.get_active_meeting_record(db)
        if rec is None:
            return MeetingTimerService._inactive_state(now)
        MeetingTimerService._apply_lazy_timeouts(db, rec, now)
        return MeetingTimerService._build_state(rec, client_id, now)

    @staticmethod
    def claim(db: Session, client_id: str) -> Dict[str, Any]:
        """认领主控：无主控（或本就是自己）时成为主控；已有他人主控则返回协助态（不报错）。"""
        now = _now()
        rec = MeetingTimerService._active(db)
        MeetingTimerService._apply_lazy_timeouts(db, rec, now)
        if rec.controller_client_id in (None, client_id):
            if rec.controller_client_id is None:
                rec.controller_version = int(rec.controller_version or 0) + 1
            rec.controller_client_id = client_id
            rec.controller_heartbeat_at = now
            if rec.timer_state is None:
                _save_ts(rec, _default_state())
            db.commit()
            db.refresh(rec)
        return MeetingTimerService._build_state(rec, client_id, now)

    @staticmethod
    def takeover(db: Session, client_id: str, expected_version: Optional[int] = None) -> Dict[str, Any]:
        """协助端接管：仅当主控已释放（null）时可接管；CAS 版本防并发抢占。计时保持暂停，待新主控继续。"""
        now = _now()
        rec = MeetingTimerService._active(db)
        MeetingTimerService._apply_lazy_timeouts(db, rec, now)
        if rec.controller_client_id is not None:
            raise ControllerPresent()
        if expected_version is not None and int(rec.controller_version or 0) != expected_version:
            raise VersionConflict()
        rec.controller_client_id = client_id
        rec.controller_heartbeat_at = now
        rec.controller_version = int(rec.controller_version or 0) + 1
        db.commit()
        db.refresh(rec)
        return MeetingTimerService._build_state(rec, client_id, now)

    @staticmethod
    def heartbeat(db: Session, client_id: str) -> Dict[str, Any]:
        """主控心跳：刷新存活；若处于「掉线自动暂停」则自动继续（重连续上）。"""
        now = _now()
        rec = MeetingTimerService._active(db)
        # 先用旧心跳做惰性判定（可能自动暂停/释放）
        MeetingTimerService._apply_lazy_timeouts(db, rec, now)
        if rec.controller_client_id == client_id:
            rec.controller_heartbeat_at = now
            ts = _ts(rec)
            if ts["status"] == "paused" and ts.get("paused_reason") == "controller_offline":
                _resume(ts, now)   # 3min 内重连自动继续
                _save_ts(rec, ts)
            db.commit()
            db.refresh(rec)
        return MeetingTimerService._build_state(rec, client_id, now)

    @staticmethod
    def control(db: Session, client_id: str, action: str, payload: Optional[dict] = None) -> Dict[str, Any]:
        """主控计时控制：resume(开始/继续) / pause / select_presenter。仅主控可调。"""
        now = _now()
        payload = payload or {}
        rec = MeetingTimerService._active(db)
        MeetingTimerService._apply_lazy_timeouts(db, rec, now)
        if rec.controller_client_id != client_id:
            raise NotController()
        rec.controller_heartbeat_at = now   # 主控在操作 → 视为存活
        ts = _ts(rec)

        if action == "resume":
            if ts["status"] != "running":
                _resume(ts, now)
        elif action == "pause":
            if ts["status"] == "running":
                _settle(ts, now)
                ts["status"] = "paused"
                ts["paused_reason"] = "manual"
        elif action == "select_presenter":
            key = payload.get("presenter_key")
            # 同一汇报人不重置其计时段（主控浏览同一人不同项目时不结算）
            if key != ts.get("current_presenter_key"):
                # 先结算上一位汇报人（仅运行中），再切到新汇报人
                if ts["status"] == "running":
                    _settle(ts, now)
                    ts["total_started_at"] = now.isoformat()   # 总时长持续走
                ts["current_presenter_key"] = key
                ts["segment_started_at"] = now.isoformat() if (key and ts["status"] == "running") else None
        else:
            raise ValueError(f"unknown timer action: {action}")

        _save_ts(rec, ts)
        db.commit()
        db.refresh(rec)
        return MeetingTimerService._build_state(rec, client_id, now)
