"""系统设置服务：通用 key-value 配置 + 周例会状态/次数逻辑。

周会次数按自然周递增：同一自然周次数恒定，跨周 +1。
"""
from datetime import date, datetime, timedelta
from typing import Optional
import json
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
# 周会自动催更的运行时开关（每周五/周日自动在核心群催更）
AUTO_REMINDER_ENABLED_KEY = "auto_reminder_enabled"
# 本实例飞书机器人应用凭证（在「系统设置 › 其他设置」配置，DB 优先于 .env，实现各实例独立机器人）
FEISHU_APP_ID_KEY = "feishu_app_id"
FEISHU_APP_SECRET_KEY = "feishu_app_secret"
# 周会汇报页：汇报顺序（部门级 + 个人级）与计时设置
MEETING_REPORT_ORDER_KEY = "meeting_report_order"
MEETING_TOTAL_MINUTES_KEY = "meeting_total_minutes"
MEETING_PERSON_THRESHOLD_MINUTES_KEY = "meeting_person_threshold_minutes"
DEFAULT_MEETING_TOTAL_MINUTES = 120
DEFAULT_MEETING_PERSON_THRESHOLD_MINUTES = 5
# 自动定时催办配置（JSON）：按负责人私聊催办的定时设置
FOLLOWUP_AUTO_KEY = "followup_auto"
DEFAULT_FOLLOWUP_AUTO = {
    "enabled": False,
    "mode": "weekly",          # weekly | fixed_days | follow_meeting
    "weekday": 4,              # 0=周一..6=周日（weekly 模式）
    "time": "14:00",          # HH:mm（weekly / fixed_days）
    "interval_days": 7,        # 3-15（fixed_days 模式）
    "follow": ["one"],        # follow_meeting 模式：one=周五① two=周日②
    "last_run_date": "",      # 防当天重复（YYYY-MM-DD）
}

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
    def get_auto_reminder_enabled(db: Session) -> bool:
        """读取周会自动催更的运行时开关（默认关闭）。"""
        return SettingsService.get_setting(db, AUTO_REMINDER_ENABLED_KEY, "false") == "true"

    @staticmethod
    def set_auto_reminder_enabled(db: Session, enabled: bool) -> None:
        """设置周会自动催更的运行时开关（每周五/周日自动催更）。"""
        SettingsService.set_setting(db, AUTO_REMINDER_ENABLED_KEY, "true" if enabled else "false")

    @staticmethod
    def get_feishu_app_id(db: Session) -> str:
        """本实例飞书 App ID：DB 优先，空则回退 .env。"""
        v = (SettingsService.get_setting(db, FEISHU_APP_ID_KEY, "") or "").strip()
        return v or get_settings().FEISHU_APP_ID

    @staticmethod
    def is_feishu_secret_set(db: Session) -> bool:
        """是否已配置 App Secret（DB 或 .env 任一非空）。不回传密钥本身。"""
        v = (SettingsService.get_setting(db, FEISHU_APP_SECRET_KEY, "") or "").strip()
        return bool(v or get_settings().FEISHU_APP_SECRET)

    @staticmethod
    def set_feishu_app(db: Session, app_id: str, app_secret: Optional[str] = None) -> None:
        """保存本实例飞书应用凭证。app_id 总是写入（空=清空，回退 .env）；
        app_secret 仅在提供且非空时更新（留空表示保持现有密钥）。"""
        SettingsService.set_setting(db, FEISHU_APP_ID_KEY, (app_id or "").strip())
        if app_secret is not None and app_secret.strip():
            SettingsService.set_setting(db, FEISHU_APP_SECRET_KEY, app_secret.strip())

    # ---------- 周会汇报页：顺序 + 计时设置 ----------

    @staticmethod
    def get_meeting_report_order(db: Session) -> dict:
        """读取汇报顺序：{departments:[...], members:{部门:[人,...]}}。未设置/损坏返回空结构。"""
        raw = SettingsService.get_setting(db, MEETING_REPORT_ORDER_KEY, "")
        if not raw:
            return {"departments": [], "members": {}}
        try:
            data = json.loads(raw)
        except (ValueError, TypeError):
            return {"departments": [], "members": {}}
        return {
            "departments": data.get("departments") or [],
            "members": data.get("members") or {},
        }

    @staticmethod
    def set_meeting_report_order(db: Session, departments: list, members: dict) -> None:
        """保存汇报顺序（部门级 + 个人级）。中文不转义。"""
        SettingsService.set_setting(
            db,
            MEETING_REPORT_ORDER_KEY,
            json.dumps({"departments": departments, "members": members}, ensure_ascii=False),
        )

    @staticmethod
    def get_meeting_total_minutes(db: Session) -> int:
        """总时长提醒阈值（分钟），默认 120。超过即在前端变色提醒（不强制结束）。"""
        return int(SettingsService.get_setting(
            db, MEETING_TOTAL_MINUTES_KEY, str(DEFAULT_MEETING_TOTAL_MINUTES)))

    @staticmethod
    def set_meeting_total_minutes(db: Session, minutes: int) -> None:
        SettingsService.set_setting(db, MEETING_TOTAL_MINUTES_KEY, str(minutes))

    @staticmethod
    def get_meeting_person_threshold_minutes(db: Session) -> int:
        """单人汇报提醒阈值（分钟），默认 5。"""
        return int(SettingsService.get_setting(
            db, MEETING_PERSON_THRESHOLD_MINUTES_KEY,
            str(DEFAULT_MEETING_PERSON_THRESHOLD_MINUTES)))

    @staticmethod
    def set_meeting_person_threshold_minutes(db: Session, minutes: int) -> None:
        SettingsService.set_setting(db, MEETING_PERSON_THRESHOLD_MINUTES_KEY, str(minutes))

    # ---------- 自动定时催办（按负责人私聊）配置 ----------

    @staticmethod
    def get_followup_auto(db: Session) -> dict:
        """读取自动定时催办配置；未设置/损坏返回默认（禁用）。"""
        raw = SettingsService.get_setting(db, FOLLOWUP_AUTO_KEY, "")
        cfg = dict(DEFAULT_FOLLOWUP_AUTO)
        if raw:
            try:
                data = json.loads(raw)
                if isinstance(data, dict):
                    cfg.update({k: data[k] for k in DEFAULT_FOLLOWUP_AUTO if k in data})
            except (ValueError, TypeError):
                pass
        return cfg

    @staticmethod
    def set_followup_auto(db: Session, cfg: dict) -> dict:
        """保存自动定时催办配置（合并进默认，保留 last_run_date 若未传）。"""
        merged = dict(DEFAULT_FOLLOWUP_AUTO)
        current = SettingsService.get_followup_auto(db)
        merged.update(current)
        merged.update({k: cfg[k] for k in DEFAULT_FOLLOWUP_AUTO if k in cfg})
        SettingsService.set_setting(db, FOLLOWUP_AUTO_KEY, json.dumps(merged, ensure_ascii=False))
        return merged

    @staticmethod
    def _base(db: Session) -> tuple[date, int]:
        bm = SettingsService.get_setting(db, MEETING_BASE_MONDAY, DEFAULT_BASE_MONDAY)
        bc = int(SettingsService.get_setting(db, MEETING_BASE_COUNT, str(DEFAULT_BASE_COUNT)))
        return date.fromisoformat(bm), bc

    @staticmethod
    def get_last_meeting_record(db: Session) -> dict:
        """最近一次周会（按 session 最大）。表为空时回退用 base 锚点作为“上次周会”，
        实现从“自然周”到“事件驱动”的平滑迁移（无需 seed 数据）。
        返回 {session:int, meeting_date:date, status:str, ended_at:datetime|None}，恒非 None。"""
        rec = db.query(MeetingRecord).order_by(MeetingRecord.session.desc()).first()
        if rec:
            return {"session": rec.session, "meeting_date": rec.meeting_date,
                    "status": rec.status, "ended_at": rec.ended_at}
        base_monday, base_count = SettingsService._base(db)
        return {"session": base_count, "meeting_date": base_monday,
                "status": "archived", "ended_at": None}

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
        表空时回退 base 锚点。新规则：上次周会结束日期 + NEW_CYCLE_DAYS 天即可进入新周期。"""
        if today is None:
            today = datetime.now().date()
        base_monday, base_count = SettingsService._base(db)
        active = SettingsService.get_setting(db, MEETING_ACTIVE, "false") == "true"
        new_cycle_days = get_settings().NEW_CYCLE_DAYS

        active_rec = SettingsService.get_active_meeting_record(db)
        last = SettingsService.get_last_meeting_record(db)  # 表→回退 base，恒非 None

        # 当前周会次数：进行中则用其 session，否则用最近一次的次数
        current_count = active_rec.session if active_rec else last["session"]

        # 距上次周会“结束日期”天数（以归档结束时刻 ended_at 为锚点；
        # 缺失结束时间时回退会议日期，兼容历史记录与校准基准数据）
        ended_at = last.get("ended_at")
        basis_date = ended_at.date() if ended_at else last["meeting_date"]
        days_since_last = (today - basis_date).days if basis_date else None

        # 能否进入新周期：无进行中的周会 且 距上次周会结束日期 ≥ NEW_CYCLE_DAYS
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
                "date": basis_date.isoformat() if basis_date else None,
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
