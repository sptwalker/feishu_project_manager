"""周会"上一次/冷却期"应以"真正召开过"为准（started_at 已设）。

回归 bug：自动开启把"下一次"周会以未来日期(下周一)、active 建出来；
一旦它被归档但从未真正召开(started_at=None)，系统却把它当成"上一次周会"
并以其日期锚定冷却期 → 把今天才要开的会显示成上次会。
"""
import pytest
from datetime import date, datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.db.base import Base
from backend.models.meeting_record import MeetingRecord
from backend.services.settings_service import SettingsService


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    S = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = S()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def _rec(db, session, meeting_date, ended_at=None, started_at=None, status="archived"):
    r = MeetingRecord(session=session, meeting_date=meeting_date, status=status,
                      content_snapshot=[], ended_at=ended_at, started_at=started_at)
    db.add(r); db.commit(); db.refresh(r)
    return r


def test_draft_meeting_not_treated_as_last(db_session):
    """已召开 #24(6/12) + 自动开启未召开 #25(6/22,started_at=None)：
    上一次应为 #24/6-12，冷却以 6/12 计，下一次=25 现在即可开。"""
    _rec(db_session, 24, date(2026, 6, 12), ended_at=datetime(2026, 6, 12, 15, 0),
         started_at=datetime(2026, 6, 12, 14, 0))
    _rec(db_session, 25, date(2026, 6, 22), ended_at=datetime(2026, 6, 22, 9, 0),
         started_at=None)  # 自动开启后被归档、从未真正召开
    s = SettingsService.get_meeting_state(db_session, today=date(2026, 6, 22))
    assert s["last_meeting"]["date"] == "2026-06-12"
    assert s["last_meeting"]["count"] == 24
    assert s["this_week_count"] == 24
    assert s["can_open_new_cycle"] is True       # 距 6/12 已 10 天
    assert s["next_count"] == 25


def test_conducted_draft_becomes_last_after_conducting(db_session):
    """#25 真正召开(started_at 已设)后，它才成为'上一次'。"""
    _rec(db_session, 24, date(2026, 6, 12), ended_at=datetime(2026, 6, 12, 15, 0),
         started_at=datetime(2026, 6, 12, 14, 0))
    _rec(db_session, 25, date(2026, 6, 22), ended_at=datetime(2026, 6, 22, 11, 0),
         started_at=datetime(2026, 6, 22, 10, 0))
    s = SettingsService.get_meeting_state(db_session, today=date(2026, 6, 23))
    assert s["last_meeting"]["count"] == 25
    assert s["last_meeting"]["date"] == "2026-06-22"


def test_fallback_to_max_when_none_conducted(db_session):
    """无任何'已召开'记录(全 started_at=None)：回退最大 session，行为不变(兼容)。"""
    _rec(db_session, 22, date(2026, 6, 3), started_at=None)
    s = SettingsService.get_meeting_state(db_session, today=date(2026, 6, 22))
    assert s["last_meeting"]["count"] == 22


def test_short_meeting_not_held(db_session):
    """启动了汇报但时长不足（<60分钟）的会不算'真正召开'，不成为上一次。"""
    # #29 真正开过：09-04 启动 14:00→15:30（90 分钟 ≥ 60）
    _rec(db_session, 29, date(2026, 9, 4), ended_at=datetime(2026, 9, 4, 15, 30),
         started_at=datetime(2026, 9, 4, 14, 0))
    # #30 启动但只开了 20 分钟（< 60）→ 不算
    _rec(db_session, 30, date(2026, 9, 11), ended_at=datetime(2026, 9, 11, 10, 20),
         started_at=datetime(2026, 9, 11, 10, 0))
    s = SettingsService.get_meeting_state(db_session, today=date(2026, 9, 12))
    assert s["last_meeting"]["count"] == 29
    assert s["last_meeting"]["date"] == "2026-09-04"


def test_next_count_increments_even_within_cooldown(db_session):
    """真正召开过 #25(6/21) 后，冷却期内下一次仍递进为 #26（冷却只决定何时能开）。"""
    _rec(db_session, 25, date(2026, 6, 21), ended_at=datetime(2026, 6, 21, 15, 30),
         started_at=datetime(2026, 6, 21, 14, 0))
    s = SettingsService.get_meeting_state(db_session, today=date(2026, 6, 22))
    assert s["last_meeting"]["count"] == 25          # 上一次仍是 25
    assert s["can_open_new_cycle"] is False          # 6/21+3=6/24，冷却未过
    assert s["next_count"] == 26                     # 下一次递进为 26
