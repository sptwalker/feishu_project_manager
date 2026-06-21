"""周会次数校准（set_count）：meeting_records 为真相源时校准必须生效。

回归 bug：set_count 在无进行中周会时写 MEETING_BASE_COUNT，
但 get_meeting_state 在表非空时只读 max(session)，base_count 被忽略
→ 校准静默失效、次数锁死，无法手动纠正。
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
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


TODAY = date(2026, 6, 21)


def _add_record(db, session, status="archived", meeting_date=date(2026, 6, 3), ended_at=None):
    rec = MeetingRecord(session=session, status=status, meeting_date=meeting_date,
                        content_snapshot=[], ended_at=ended_at)
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return rec


def test_calibrate_changes_count_when_record_exists(db_session):
    """核心回归：有归档记录时校准必须真正改变 get_meeting_state 的次数。"""
    _add_record(db_session, 22)
    SettingsService.set_count(db_session, 30, today=TODAY)
    state = SettingsService.get_meeting_state(db_session, today=TODAY)
    assert state["this_week_count"] == 30        # 当前次数已被校准
    # 最近一次记录已改名为 30
    rec = db_session.query(MeetingRecord).order_by(MeetingRecord.session.desc()).first()
    assert rec.session == 30


def test_calibrate_is_idempotent_roundtrip(db_session):
    """校准到 N 后，再次读到的当前次数仍是 N（可重复纠正，不锁死）。"""
    _add_record(db_session, 24, meeting_date=TODAY, ended_at=datetime(2026, 6, 21, 15, 0))
    SettingsService.set_count(db_session, 18, today=TODAY)
    assert SettingsService.get_meeting_state(db_session, today=TODAY)["this_week_count"] == 18
    SettingsService.set_count(db_session, 19, today=TODAY)
    assert SettingsService.get_meeting_state(db_session, today=TODAY)["this_week_count"] == 19


def test_calibrate_empty_table_seeds_base(db_session):
    """表为空（从未开会）时校准写 base 锚点并生效。"""
    SettingsService.set_count(db_session, 7, today=TODAY)
    assert SettingsService.get_meeting_state(db_session, today=TODAY)["this_week_count"] == 7


def test_calibrate_active_meeting_updates_active(db_session):
    """进行中的周会校准直接改其 session。"""
    _add_record(db_session, 10, status="active", meeting_date=TODAY)
    SettingsService.set_count(db_session, 13, today=TODAY)
    state = SettingsService.get_meeting_state(db_session, today=TODAY)
    assert state["this_week_count"] == 13
    assert state["this_week_recorded"] is True


def test_calibrate_conflict_raises(db_session):
    """目标次数已被其它记录占用 → 拒绝（session 唯一，不静默删历史）。"""
    _add_record(db_session, 20)
    _add_record(db_session, 24)  # latest
    with pytest.raises(ValueError):
        SettingsService.set_count(db_session, 20, today=TODAY)
