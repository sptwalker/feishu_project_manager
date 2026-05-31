"""系统设置服务：通用 key-value 配置 + 周例会状态/次数逻辑。

周会次数按自然周递增：同一自然周次数恒定，跨周 +1。
"""
from datetime import date, datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session

from backend.models.system_setting import SystemSetting
from backend.models.project import Project

# 配置键
MEETING_ACTIVE = "meeting_active"
MEETING_BASE_MONDAY = "meeting_base_monday"
MEETING_BASE_COUNT = "meeting_base_count"

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
    def _base(db: Session) -> tuple[date, int]:
        bm = SettingsService.get_setting(db, MEETING_BASE_MONDAY, DEFAULT_BASE_MONDAY)
        bc = int(SettingsService.get_setting(db, MEETING_BASE_COUNT, str(DEFAULT_BASE_COUNT)))
        return date.fromisoformat(bm), bc

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
        if today is None:
            today = datetime.now().date()
        base_monday, base_count = SettingsService._base(db)
        active = SettingsService.get_setting(db, MEETING_ACTIVE, "false") == "true"

        tw_monday = monday_of(today)
        tw_count = compute_count(today, base_monday, base_count)

        records = SettingsService.scan_meeting_records(db)
        this_week_recorded = any(r["session"] == tw_count for r in records)
        prior = [r for r in records if r["session"] < tw_count]
        last = max(prior, key=lambda r: r["session"]) if prior else None

        # 校准目标：本周已召开 -> 下周；本周未召开 -> 本周
        if this_week_recorded:
            cal_monday = tw_monday + timedelta(days=7)
            cal_count = tw_count + 1
        else:
            cal_monday = tw_monday
            cal_count = tw_count

        return {
            "active": active,
            "base_monday": base_monday.isoformat(),
            "base_count": base_count,
            "this_week_monday": tw_monday.isoformat(),
            "this_week_count": tw_count,
            "this_week_recorded": this_week_recorded,
            "last_meeting": ({"date": last["time"], "count": last["session"]} if last else None),
            "calibration_count": cal_count,
            "calibration_monday": cal_monday.isoformat(),
        }

    @staticmethod
    def set_active(db: Session, active: bool) -> None:
        SettingsService.set_setting(db, MEETING_ACTIVE, "true" if active else "false")

    @staticmethod
    def set_count(db: Session, count: int, today: Optional[date] = None) -> None:
        """以校准目标周一为基准，重设 base_monday / base_count"""
        state = SettingsService.get_meeting_state(db, today)
        SettingsService.set_setting(db, MEETING_BASE_MONDAY, state["calibration_monday"])
        SettingsService.set_setting(db, MEETING_BASE_COUNT, str(count))
