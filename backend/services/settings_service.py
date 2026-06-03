"""系统设置服务：通用 key-value 配置 + 周例会状态/次数逻辑。

周会次数按自然周递增：同一自然周次数恒定，跨周 +1。
"""
from datetime import date, datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session

from backend.models.system_setting import SystemSetting
from backend.models.project import Project
from backend.models.meeting_record import MeetingRecord
from backend.core.config import get_settings

# 配置键
MEETING_ACTIVE = "meeting_active"
MEETING_BASE_MONDAY = "meeting_base_monday"
MEETING_BASE_COUNT = "meeting_base_count"
# 周会纪要分享的核心组群 chat_id（在「系统设置 › 其他设置」配置）
FEISHU_CORE_GROUP_CHAT_ID_KEY = "feishu_core_group_chat_id"
# 周四自动开周会的运行时开关（在「系统设置 › 其他设置」配置，改后立即生效无需重启）
AUTO_OPEN_MEETING_ENABLED_KEY = "auto_open_meeting_enabled"

# 默认基准：2026-06-01（周一）= 第 22 次
DEFAULT_BASE_MONDAY = "2026-06-01"
DEFAULT_BASE_COUNT = 22


def monday_of(d: date) -> date:
    """返回 d 所在自然周的周一（weekday: Mon=0..Sun=6）"""
    return d - timedelta(days=d.weekday())


def compute_count(target: date, base_monday: date, base_count: int) -> int:
    """计算 target 所在自然周的周会次数"""
    weeks = (monday_of(target) - base_monday).days // 7
    return base_count + weeks


class SettingsService:
    """系统设置服务"""

    @staticmethod
    def get_setting(db: Session, key: str, default: Optional[str] = None) -> Optional[str]:
        s = db.query(SystemSetting).filter(SystemSetting.key == key).first()
        return s.value if s and s.value is not None else default

    @staticmethod
    def set_setting(db: Session, key: str, value: str) -> SystemSetting:
        s = db.query(SystemSetting).filter(SystemSetting.key == key).first()
        if s:
            s.value = value
        else:
            s = SystemSetting(key=key, value=value)
            db.add(s)
        try:
            db.commit()
            db.refresh(s)
        except Exception:
            db.rollback()
            raise
        return s

    @staticmethod
    def get_core_group_chat_id(db: Session) -> Optional[str]:
        """读取周会纪要核心群 chat_id（纯 DB，所见即所得）；空字符串归一为 None=不发送"""
        val = SettingsService.get_setting(db, FEISHU_CORE_GROUP_CHAT_ID_KEY, "")
        val = (val or "").strip()
        return val or None

    @staticmethod
    def get_auto_open_meeting_enabled(db: Session) -> bool:
        """读取周四自动开周会的运行时开关（默认关闭）。"""
        return SettingsService.get_setting(db, AUTO_OPEN_MEETING_ENABLED_KEY, "false") == "true"

    @staticmethod
    def set_auto_open_meeting_enabled(db: Session, enabled: bool) -> None:
        """设置周四自动开周会的运行时开关。"""
        SettingsService.set_setting(db, AUTO_OPEN_MEETING_ENABLED_KEY, "true" if enabled else "false")

    @staticmethod
    def _base(db: Session) -> tuple[date, int]:
        bm = SettingsService.get_setting(db, MEETING_BASE_MONDAY, DEFAULT_BASE_MONDAY)
        bc = int(SettingsService.get_setting(db, MEETING_BASE_COUNT, str(DEFAULT_BASE_COUNT)))
        return date.fromisoformat(bm), bc

    @staticmethod
    def get_last_meeting_record(db: Session) -> dict:
        """最近一次周会（按 session 最大）。表为空时回退用 base 锚点作为“上次周会”，
        实现从“自然周”到“事件驱动”的平滑迁移（无需 seed 数据）。
        返回 {session:int, meeting_date:date, status:str}，恒非 None。"""
        rec = db.query(MeetingRecord).order_by(MeetingRecord.session.desc()).first()
        if rec:
            return {"session": rec.session, "meeting_date": rec.meeting_date, "status": rec.status}
        base_monday, base_count = SettingsService._base(db)
        return {"session": base_count, "meeting_date": base_monday, "status": "archived"}

    @staticmethod
    def get_active_meeting_record(db: Session) -> Optional[MeetingRecord]:
        """当前进行中的周会（status=active），无则 None。"""
        return db.query(MeetingRecord).filter(MeetingRecord.status == "active").first()

    @staticmethod
    def scan_meeting_records(db: Session) -> list[dict]:
        """扫描各项目 progress_log，收集带 meeting_session 的周会记录"""
        records: list[dict] = []
        for p in db.query(Project).all():
            for entry in (p.progress_log or []):
                if isinstance(entry, dict) and entry.get("meeting_session") is not None:
                    records.append({
                        "session": int(entry["meeting_session"]),
                        "time": entry.get("time", ""),
                    })
        return records

    @staticmethod
    def get_meeting_state(db: Session, today: Optional[date] = None) -> dict:
        """周会状态（事件驱动）：周期次数与“能否开新周期”由 meeting_records 表驱动，
        表空时回退 base 锚点。新规则：上次会议日期 + NEW_CYCLE_DAYS 天即可进入新周期。"""
        if today is None:
            today = datetime.now().date()
        base_monday, base_count = SettingsService._base(db)
        active = SettingsService.get_setting(db, MEETING_ACTIVE, "false") == "true"
        new_cycle_days = get_settings().NEW_CYCLE_DAYS

        active_rec = SettingsService.get_active_meeting_record(db)
        last = SettingsService.get_last_meeting_record(db)  # 表→回退 base，恒非 None

        # 当前周会次数：进行中则用其 session，否则用最近一次的次数
        current_count = active_rec.session if active_rec else last["session"]

        # 距上次会议日期天数（以会议日期为锚点）
        last_date = last["meeting_date"]
        days_since_last = (today - last_date).days if last_date else None

        # 能否进入新周期：无进行中的周会 且 距上次会议日期 ≥ NEW_CYCLE_DAYS
        can_open_new_cycle = (active_rec is None) and (
            days_since_last is not None and days_since_last >= new_cycle_days
        )
        # 下次开启次数：进入新周期 +1，否则重开当前次（不跳号）
        next_count = (last["session"] + 1) if can_open_new_cycle else current_count

        tw_monday = monday_of(today)

        return {
            "active": active,
            "base_monday": base_monday.isoformat(),
            "base_count": base_count,
            "this_week_monday": tw_monday.isoformat(),
            "this_week_count": current_count,             # 重定义：当前周期次数
            "this_week_recorded": active_rec is not None,  # 重定义：是否正在记录中
            "last_meeting": {
                "date": last_date.isoformat() if last_date else None,
                "count": last["session"],
            },
            "calibration_count": next_count,              # 兼容旧字段：前端开启取用的次数
            "calibration_monday": tw_monday.isoformat(),  # 保留派生（不再用于周期判断）
            # 新增（事件驱动）
            "can_open_new_cycle": can_open_new_cycle,
            "next_count": next_count,
            "days_since_last": days_since_last,
            "new_cycle_days": new_cycle_days,
        }

    @staticmethod
    def set_active(db: Session, active: bool) -> None:
        SettingsService.set_setting(db, MEETING_ACTIVE, "true" if active else "false")

    @staticmethod
    def set_count(db: Session, count: int, today: Optional[date] = None) -> None:
        """校准周会次数基准。进行中的周会直接改其 session；否则把 base_count 设为锚点。
        （前端在 active 期间禁用校准，避免改动正在记录的周会次数导致进展标签错位。）"""
        active_rec = SettingsService.get_active_meeting_record(db)
        if active_rec:
            active_rec.session = count
            try:
                db.commit()
            except Exception:
                db.rollback()
                raise
        else:
            SettingsService.set_setting(db, MEETING_BASE_COUNT, str(count))
