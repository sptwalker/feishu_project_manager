"""图片上传 / 访问测试

- 拒绝非 JPG/PNG
- 拒绝超过 10MB
- 上传成功返回 url，GET 能取回文件
- 非管理员（observer）无上传权限
"""
import io
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
from backend.core.config import get_settings


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    db = sessionmaker(autocommit=False, autoflush=False, bind=engine)()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def admin_user(db_session):
    u = User(feishu_user_id="upl_admin", name="上传管理员", role=UserRole.ADMIN)
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)
    return u


@pytest.fixture
def observer_user(db_session):
    u = User(feishu_user_id="upl_obs", name="观察者", role=UserRole.OBSERVER)
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)
    return u


def _client(db_session, user):
    def override_db():
        try:
            yield db_session
        finally:
            pass

    def override_user():
        return user

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = override_user
    return TestClient(app)


@pytest.fixture(autouse=True)
def _tmp_upload_dir(tmp_path):
    """每个测试用独立临时上传目录，避免污染真实 data/uploads。"""
    s = get_settings()
    old = s.UPLOAD_DIR
    s.UPLOAD_DIR = str(tmp_path / "uploads")
    yield
    s.UPLOAD_DIR = old


# 最小合法 PNG（1x1 透明）字节
_PNG_1x1 = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4"
    "890000000a49444154789c6360000002000154a24f5f0000000049454e44ae426082"
)


def test_upload_png_ok_and_fetch(db_session, admin_user):
    client = _client(db_session, admin_user)
    r = client.post("/api/v1/uploads/image",
                    files={"file": ("a.png", io.BytesIO(_PNG_1x1), "image/png")})
    app.dependency_overrides.clear()
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["url"].startswith("/api/v1/uploads/")
    assert body["name"] == "a.png"
    assert body["size"] == len(_PNG_1x1)
    # GET 取回（无需鉴权）
    fname = body["url"].rsplit("/", 1)[-1]
    g = TestClient(app).get(f"/api/v1/uploads/{fname}")
    assert g.status_code == 200
    assert g.content == _PNG_1x1


def test_reject_non_image(db_session, admin_user):
    client = _client(db_session, admin_user)
    r = client.post("/api/v1/uploads/image",
                    files={"file": ("a.txt", io.BytesIO(b"hello"), "text/plain")})
    app.dependency_overrides.clear()
    assert r.status_code == 400
    assert "JPG" in r.json()["detail"]


def test_reject_oversize(db_session, admin_user):
    client = _client(db_session, admin_user)
    big = _PNG_1x1 + b"\x00" * (10 * 1024 * 1024 + 1)  # 超 10MB（content-type 仍 png）
    r = client.post("/api/v1/uploads/image",
                    files={"file": ("big.png", io.BytesIO(big), "image/png")})
    app.dependency_overrides.clear()
    assert r.status_code == 400
    assert "10MB" in r.json()["detail"]


def test_observer_cannot_upload(db_session, observer_user):
    client = _client(db_session, observer_user)
    r = client.post("/api/v1/uploads/image",
                    files={"file": ("a.png", io.BytesIO(_PNG_1x1), "image/png")})
    app.dependency_overrides.clear()
    assert r.status_code == 403


def test_fetch_path_traversal_rejected():
    r = TestClient(app).get("/api/v1/uploads/..%2f..%2fsecret")
    # 路径穿越被拒（400 非法文件名 或 404）
    assert r.status_code in (400, 404)


# ---- 视频上传 ----

# 最小合法 mp4 头：偏移 4-8 为 box 类型 "ftyp"
_MP4_HEAD = b"\x00\x00\x00\x18ftypisom" + b"\x00" * 16
# webm 的 EBML 头
_WEBM_HEAD = b"\x1aE\xdf\xa3" + b"\x00" * 16


def test_upload_mp4_ok_and_fetch(db_session, admin_user):
    client = _client(db_session, admin_user)
    r = client.post("/api/v1/uploads/video",
                    files={"file": ("clip.mp4", io.BytesIO(_MP4_HEAD), "video/mp4")})
    app.dependency_overrides.clear()
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["url"].startswith("/api/v1/uploads/")
    fname = body["url"].rsplit("/", 1)[-1]
    g = TestClient(app).get(f"/api/v1/uploads/{fname}")
    assert g.status_code == 200
    assert g.content == _MP4_HEAD
    assert g.headers["content-type"] == "video/mp4"  # 回填的 Content-Type


def test_upload_webm_ok(db_session, admin_user):
    client = _client(db_session, admin_user)
    r = client.post("/api/v1/uploads/video",
                    files={"file": ("c.webm", io.BytesIO(_WEBM_HEAD), "video/webm")})
    app.dependency_overrides.clear()
    assert r.status_code == 200, r.text


def test_reject_fake_video_magic(db_session, admin_user):
    """扩展名是 mp4 但文件头不符 → 拒绝（防改扩展名伪装）。"""
    client = _client(db_session, admin_user)
    r = client.post("/api/v1/uploads/video",
                    files={"file": ("fake.mp4", io.BytesIO(b"not a real video"), "video/mp4")})
    app.dependency_overrides.clear()
    assert r.status_code == 400
    assert "内容与格式" in r.json()["detail"]


def test_reject_non_video_ext(db_session, admin_user):
    client = _client(db_session, admin_user)
    r = client.post("/api/v1/uploads/video",
                    files={"file": ("a.png", io.BytesIO(_PNG_1x1), "image/png")})
    app.dependency_overrides.clear()
    assert r.status_code == 400


def test_observer_cannot_upload_video(db_session, observer_user):
    client = _client(db_session, observer_user)
    r = client.post("/api/v1/uploads/video",
                    files={"file": ("clip.mp4", io.BytesIO(_MP4_HEAD), "video/mp4")})
    app.dependency_overrides.clear()
    assert r.status_code == 403
