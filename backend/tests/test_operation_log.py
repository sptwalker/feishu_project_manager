"""系统操作日志服务测试"""
import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.db.base import Base
from backend.models.user import User, UserRole
from backend.models.operation_log import OperationLog
from backend.services.operation_log_service import OperationLogService


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


def _mk_user(db, name="申华", role=UserRole.MEMBER):
    u = User(feishu_user_id=f"ou_{name}", name=name, role=role)
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


# ---- log + query ----

def test_log_and_query(db_session):
    u = _mk_user(db_session)
    OperationLogService.log(db_session, user=u, action="login", description="登录了系统")
    rows = OperationLogService.query(db_session)
    assert len(rows) == 1
    assert rows[0].user_name == "申华"
    assert rows[0].action == "login"
    assert rows[0].description == "登录了系统"
    assert rows[0].user_id == u.id


def test_query_time_range_filter(db_session):
    u = _mk_user(db_session)
    base = datetime(2026, 6, 3, 10, 0)
    OperationLogService.log(db_session, user=u, action="login", description="早", occurred_at=base)
    OperationLogService.log(db_session, user=u, action="login", description="中", occurred_at=base + timedelta(hours=2))
    OperationLogService.log(db_session, user=u, action="login", description="晚", occurred_at=base + timedelta(hours=5))
    # 只取中间窗口
    rows = OperationLogService.query(db_session,
                                    start=base + timedelta(hours=1),
                                    end=base + timedelta(hours=3))
    assert [r.description for r in rows] == ["中"]


def test_query_desc_order(db_session):
    u = _mk_user(db_session)
    base = datetime(2026, 6, 3, 10, 0)
    OperationLogService.log(db_session, user=u, action="login", description="a", occurred_at=base)
    OperationLogService.log(db_session, user=u, action="login", description="b", occurred_at=base + timedelta(hours=1))
    rows = OperationLogService.query(db_session)
    assert [r.description for r in rows] == ["b", "a"]  # 倒序


def test_log_failure_does_not_raise(db_session):
    """记日志失败应被吞掉，不抛出（action=None 触发 NOT NULL 错误）"""
    u = _mk_user(db_session)
    # action 为 None 会违反 NOT NULL；log 内部应捕获
    OperationLogService.log(db_session, user=u, action=None, description="x")  # type: ignore
    # 不抛异常即通过；且会话仍可用
    assert OperationLogService.query(db_session) == []


# ---- classify_progress_change ----

def test_classify_new_progress(db_session):
    old = [{"id": "e1", "content": "a", "status": "正常"}]
    new = old + [{"id": "e2", "content": "b", "status": "正常"}]
    action, st = OperationLogService.classify_progress_change(old, new)
    assert action == "update_progress"
    assert st is None


def test_classify_feedback(db_session):
    old = [{"id": "e1", "content": "a", "status": "待确认"}]
    new = old + [{"id": "e2", "content": "ok", "status": "待确认", "reply_to": "e1"}]
    action, st = OperationLogService.classify_progress_change(old, new)
    assert action == "feedback"
    assert st == "待确认"


def test_classify_comment_annotation_added(db_session):
    old = [{"id": "e1", "content": "a", "status": "正常", "annotations": []}]
    new = [{"id": "e1", "content": "a", "status": "正常",
            "annotations": [{"id": "a1", "content": "批注", "author_name": "张三", "replies": []}]}]
    action, st = OperationLogService.classify_progress_change(old, new)
    assert action == "comment"


def test_classify_comment_reply_added(db_session):
    old = [{"id": "e1", "content": "a", "status": "正常",
            "annotations": [{"id": "a1", "content": "批注", "replies": []}]}]
    new = [{"id": "e1", "content": "a", "status": "正常",
            "annotations": [{"id": "a1", "content": "批注",
                             "replies": [{"id": "r1", "content": "回复"}]}]}]
    action, st = OperationLogService.classify_progress_change(old, new)
    assert action == "comment"


def test_classify_no_change(db_session):
    log = [{"id": "e1", "content": "a", "status": "正常", "annotations": []}]
    action, st = OperationLogService.classify_progress_change(log, log)
    assert action is None
    assert st is None


def test_classify_delete_progress(db_session):
    old = [
        {"id": "e1", "content": "a", "status": "正常"},
        {"id": "e2", "content": "b", "status": "正常"},
    ]
    new = [{"id": "e1", "content": "a", "status": "正常"}]
    action, st = OperationLogService.classify_progress_change(old, new)
    assert action == "delete_progress"
    assert st is None


def test_classify_delete_all_progress(db_session):
    old = [{"id": "e1", "content": "a", "status": "正常"}]
    action, st = OperationLogService.classify_progress_change(old, [])
    assert action == "delete_progress"


def test_classify_add_beats_delete(db_session):
    """同时增删时，新增优先于删除"""
    old = [{"id": "e1", "content": "a", "status": "正常"}]
    new = [{"id": "e2", "content": "新", "status": "正常"}]  # e1 删除、e2 新增
    action, st = OperationLogService.classify_progress_change(old, new)
    assert action == "update_progress"


def test_classify_feedback_priority_over_progress(db_session):
    """同时新增普通进展和反馈条目时，反馈优先"""
    old = [{"id": "e1", "content": "a", "status": "待确认"}]
    new = old + [
        {"id": "e2", "content": "新进展", "status": "正常"},
        {"id": "e3", "content": "反馈", "status": "待确认", "reply_to": "e1"},
    ]
    action, st = OperationLogService.classify_progress_change(old, new)
    assert action == "feedback"
