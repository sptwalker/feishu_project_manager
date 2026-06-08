"""会议计时 + 主控状态机测试

直接测 service：用真实 now，但通过手动设置 timer_state 锚点 / controller_heartbeat_at
为「过去时刻」来模拟时间流逝与掉线，断言结算/暂停/释放/重连/接管/拒绝逻辑。
"""
import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.models.meeting_record import MeetingRecord
from backend.models import User as _U, Project as _P, Task as _T, Event as _E, Risk as _R  # noqa: F401
from backend.db.base import Base
from backend.services.meeting_timer_service import (
    MeetingTimerService as TS, NotController, ControllerPresent, VersionConflict,
    OFFLINE_SECONDS, RELEASE_SECONDS,
)


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    s = sessionmaker(autocommit=False, autoflush=False, bind=engine)()
    # 建一条进行中的周会
    rec = MeetingRecord(session=1, meeting_date=datetime.now().date(), status="active")
    s.add(rec)
    s.commit()
    try:
        yield s
    finally:
        s.close()


def _rec(db):
    return db.query(MeetingRecord).filter(MeetingRecord.status == "active").first()


def test_claim_makes_controller_and_bumps_version(db):
    st = TS.claim(db, "clientA")
    assert st["my_role"] == "controller"
    assert st["controller_present"] is True
    assert st["controller_version"] == 1


def test_resume_and_select_presenter(db):
    TS.claim(db, "clientA")
    st = TS.control(db, "clientA", "resume", {})
    assert st["status"] == "running"
    assert st["total_started_at"] is not None
    st = TS.control(db, "clientA", "select_presenter", {"presenter_key": "产品|申华"})
    assert st["current_presenter_key"] == "产品|申华"
    assert st["segment_started_at"] is not None


def test_non_controller_cannot_control(db):
    TS.claim(db, "clientA")
    with pytest.raises(NotController):
        TS.control(db, "clientB", "pause", {})


def test_pause_settles_elapsed(db):
    TS.claim(db, "clientA")
    TS.control(db, "clientA", "resume", {})
    TS.control(db, "clientA", "select_presenter", {"presenter_key": "A|a"})
    # 手动把锚点改成 30 秒前，模拟已运行 30s
    rec = _rec(db)
    past = (datetime.now() - timedelta(seconds=30)).isoformat()
    ts = dict(rec.timer_state)
    ts["total_started_at"] = past
    ts["segment_started_at"] = past
    rec.timer_state = ts
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(rec, "timer_state")
    db.commit()
    st = TS.control(db, "clientA", "pause", {})
    assert st["status"] == "paused"
    assert st["paused_reason"] == "manual"
    assert 28 <= st["total_base"] <= 32
    assert 28 <= st["person_base"]["A|a"] <= 32


def test_offline_auto_pause_settles_at_heartbeat_plus_t1(db):
    """主控掉线（心跳超 T1）→ 自动暂停，结算到『最后心跳 + T1』，掉线后流逝不计入。"""
    TS.claim(db, "clientA")
    TS.control(db, "clientA", "resume", {})
    TS.control(db, "clientA", "select_presenter", {"presenter_key": "A|a"})
    rec = _rec(db)
    # 运行起点 = 60s 前；最后心跳 = 20s 前（> T1=15s → 判定掉线）
    now = datetime.now()
    ts = dict(rec.timer_state)
    ts["total_started_at"] = (now - timedelta(seconds=60)).isoformat()
    ts["segment_started_at"] = (now - timedelta(seconds=60)).isoformat()
    rec.timer_state = ts
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(rec, "timer_state")
    rec.controller_heartbeat_at = now - timedelta(seconds=20)
    db.commit()
    st = TS.get_state(db, "clientB")  # 协助端轮询触发惰性判定
    assert st["status"] == "paused"
    assert st["paused_reason"] == "controller_offline"
    # 结算到 心跳(-20s)+15s = -5s；累计 ≈ 60-5 = 55s（不含掉线后的流逝）
    assert 53 <= st["total_base"] <= 57
    assert 53 <= st["person_base"]["A|a"] <= 57


def test_reconnect_within_t2_auto_resumes(db):
    """掉线自动暂停后，原主控 3min 内重连（心跳）→ 自动继续。"""
    TS.claim(db, "clientA")
    TS.control(db, "clientA", "resume", {})
    rec = _rec(db)
    rec.controller_heartbeat_at = datetime.now() - timedelta(seconds=20)  # 掉线
    db.commit()
    TS.get_state(db, "clientB")  # 触发自动暂停
    assert _rec(db).timer_state["status"] == "paused"
    st = TS.heartbeat(db, "clientA")  # 原主控重连
    assert st["my_role"] == "controller"
    assert st["status"] == "running"
    assert st["paused_reason"] is None


def test_manual_pause_not_auto_resumed_by_heartbeat(db):
    """手动暂停不会被心跳自动唤醒（仅掉线暂停才自动继续）。"""
    TS.claim(db, "clientA")
    TS.control(db, "clientA", "resume", {})
    TS.control(db, "clientA", "pause", {})
    st = TS.heartbeat(db, "clientA")
    assert st["status"] == "paused"
    assert st["paused_reason"] == "manual"


def test_release_after_t2_and_takeover(db):
    """主控掉线超 T2 → 释放；协助端可接管，主控存在时不可接管。"""
    TS.claim(db, "clientA")
    TS.control(db, "clientA", "resume", {})
    # 主控仍在线时接管应失败
    with pytest.raises(ControllerPresent):
        TS.takeover(db, "clientB")
    # 心跳设为 200s 前（> T2=180s）
    rec = _rec(db)
    rec.controller_heartbeat_at = datetime.now() - timedelta(seconds=200)
    db.commit()
    st = TS.get_state(db, "clientB")  # 惰性释放
    assert st["controller_present"] is False
    # 释放后协助端接管成功
    st2 = TS.takeover(db, "clientB")
    assert st2["my_role"] == "controller"


def test_takeover_version_conflict(db):
    """接管 CAS：expected_version 不匹配 → 冲突。"""
    rec = _rec(db)
    rec.controller_heartbeat_at = datetime.now() - timedelta(seconds=200)
    rec.controller_client_id = "old"
    db.commit()
    TS.get_state(db, "x")  # 释放
    with pytest.raises(VersionConflict):
        TS.takeover(db, "clientB", expected_version=999)


def test_get_state_inactive_when_no_meeting(db):
    """无进行中周会时返回 inactive。"""
    _rec(db).status = "archived"
    db.commit()
    st = TS.get_state(db, "clientA")
    assert st["active"] is False
    assert st["my_role"] == "none"


def test_thresholds_exposed(db):
    st = TS.claim(db, "clientA")
    assert st["offline_seconds"] == OFFLINE_SECONDS
    assert st["release_seconds"] == RELEASE_SECONDS
