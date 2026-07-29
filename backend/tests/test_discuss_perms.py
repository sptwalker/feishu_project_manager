"""留言区细粒度授权（discuss_perms）测试

覆盖：
- 无权用户调 留言后台各动作端点 → 403；授对应权限后 → 通过。
- 查看列表需任一权限；有权即可查看。
- UserResponse 把 CSV 串暴露成 list；UserUpdate 只接受白名单键（非法键被过滤）。
- 评星并入 reply 权限。
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.main import app
from backend.models.user import User, UserRole
from backend.models import User as _U, Project as _P, Task as _T, Event as _E, Risk as _R  # noqa: F401
from backend.db.base import Base
from backend.api.deps import get_db
from backend.core.dependencies import get_current_user
from backend.discuss.db import get_discuss_db
from backend.discuss.models import DiscussBase, DiscussUser
from backend.discuss.service import DiscussService as S
from backend.schemas.user import UserResponse, UserUpdate


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite:///:memory:", echo=False,
        connect_args={"check_same_thread": False}, poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = Session()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def ddb_session():
    engine = create_engine(
        "sqlite:///:memory:", echo=False,
        connect_args={"check_same_thread": False}, poolclass=StaticPool,
    )
    DiscussBase.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    ddb = Session()
    # 一个外部用户 + 一楼留言（走 service 建，保证 board_id/thread_id 等不变式正确）
    u = DiscussUser(email="ext@x.com", nickname="小客", phone="1", status="active")
    ddb.add(u)
    ddb.commit()
    ddb.refresh(u)
    m = S.post_message(ddb, u, "求助一下")
    try:
        yield ddb, u, m
    finally:
        ddb.close()


def _client(db_session, ddb_session, perms: str):
    ddb, _, _ = ddb_session
    user = User(feishu_user_id="perm_user", name="内部员工", role=UserRole.MEMBER, discuss_perms=perms)

    def override_get_db():
        yield db_session

    def override_ddb():
        yield ddb

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_discuss_db] = override_ddb
    app.dependency_overrides[get_current_user] = lambda: user
    return TestClient(app)


def teardown_function():
    app.dependency_overrides.clear()


# ---- 端点门控 ----

def test_reply_denied_without_perm(db_session, ddb_session):
    _, _, m = ddb_session
    c = _client(db_session, ddb_session, "")
    r = c.post("/api/v1/discuss/admin/reply", json={"thread_id": m.id, "content": "hi"})
    assert r.status_code == 403


def test_reply_allowed_with_perm(db_session, ddb_session):
    _, _, m = ddb_session
    c = _client(db_session, ddb_session, "reply")
    r = c.post("/api/v1/discuss/admin/reply", json={"thread_id": m.id, "content": "hi"})
    assert r.status_code == 200


def test_star_uses_reply_perm(db_session, ddb_session):
    _, _, m = ddb_session
    assert _client(db_session, ddb_session, "").put(
        "/api/v1/discuss/admin/star", json={"message_id": m.id, "star": 3}).status_code == 403
    assert _client(db_session, ddb_session, "reply").put(
        "/api/v1/discuss/admin/star", json={"message_id": m.id, "star": 3}).status_code == 200


def test_hide_perm(db_session, ddb_session):
    _, _, m = ddb_session
    assert _client(db_session, ddb_session, "reply").put(
        "/api/v1/discuss/admin/visibility", json={"message_id": m.id, "visible": False}).status_code == 403
    assert _client(db_session, ddb_session, "hide").put(
        "/api/v1/discuss/admin/visibility", json={"message_id": m.id, "visible": False}).status_code == 200


def test_block_perm(db_session, ddb_session):
    _, u, _ = ddb_session
    assert _client(db_session, ddb_session, "reply").put(
        "/api/v1/discuss/admin/block", json={"ext_user_id": u.id, "blocked": True}).status_code == 403
    assert _client(db_session, ddb_session, "block").put(
        "/api/v1/discuss/admin/block", json={"ext_user_id": u.id, "blocked": True}).status_code == 200


def test_delete_perm(db_session, ddb_session):
    _, _, m = ddb_session
    assert _client(db_session, ddb_session, "reply").delete(
        f"/api/v1/discuss/admin/threads/{m.id}").status_code == 403
    assert _client(db_session, ddb_session, "delete").delete(
        f"/api/v1/discuss/admin/threads/{m.id}").status_code == 200


def test_announce_perm(db_session, ddb_session):
    assert _client(db_session, ddb_session, "reply").put(
        "/api/v1/discuss/admin/announcement", json={"content": "x"}).status_code == 403
    assert _client(db_session, ddb_session, "announce").put(
        "/api/v1/discuss/admin/announcement", json={"content": "x"}).status_code == 200


def test_list_requires_any_perm(db_session, ddb_session):
    assert _client(db_session, ddb_session, "").get(
        "/api/v1/discuss/admin/threads").status_code == 403
    assert _client(db_session, ddb_session, "hide").get(
        "/api/v1/discuss/admin/threads").status_code == 200


# ---- schema ----

def test_response_splits_csv():
    from datetime import datetime
    from backend.models.user import UserStatus
    u = User(feishu_user_id="x", name="n", role=UserRole.ADMIN,
             status=UserStatus.ACTIVE, discuss_perms="reply,delete")
    # 补齐 UserResponse 必填的时间戳字段（未落库，无 server_default）
    u.id, u.created_at, u.updated_at = 1, datetime.now(), datetime.now()
    resp = UserResponse.model_validate(u)
    assert resp.discuss_perms == ["reply", "delete"]


def test_update_filters_unknown_keys():
    upd = UserUpdate(discuss_perms=["reply", "bogus", "delete", "reply"])
    assert upd.discuss_perms == ["reply", "delete"]  # 去重 + 白名单过滤
