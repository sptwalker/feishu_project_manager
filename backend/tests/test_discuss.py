"""留言讨论区测试

覆盖：验证码（冷却/上限/错误作废/消费）、注册（IP 限制/重复邮箱）、登录、
发帖（楼结构/他人楼禁止/限流/封禁）、内部回复（replied 标记）、星级、隐藏、
未回复筛选与搜索、公开视图不含隐私、独立 JWT 与内部 token 不互认。
"""
import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.discuss.db import DiscussBase, reset_discuss_engine_for_tests
from backend.discuss import models as dmodels  # noqa: F401 - 注册表
from backend.discuss.models import DiscussUser, DiscussCode, DiscussMessage
from backend.discuss.service import (
    DiscussService as S, DiscussError, create_ext_token, verify_ext_token,
    CODE_RESEND_SECONDS, POST_MIN_INTERVAL_SECONDS,
)
from backend.core.security import verify_token as verify_internal_token


@pytest.fixture
def ddb():
    """独立内存 discuss 库"""
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    DiscussBase.metadata.create_all(engine)
    factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    reset_discuss_engine_for_tests(engine, factory)
    db = factory()
    try:
        yield db
    finally:
        db.close()


SMTP_OFF = {"host": "", "port": 465, "ssl": True, "username": "", "password": "", "sender": ""}


def _get_code(ddb, email):
    """测试后门：从库里拿不到明文码，直接构造已知验证码"""
    import hashlib
    rec = ddb.query(DiscussCode).filter(DiscussCode.email == email).first()
    rec.code_hash = hashlib.sha256(b"123456").hexdigest()
    ddb.commit()
    return "123456"


def _register(ddb, email="a@x.com", nick="小明", phone="13800000000", ip="1.2.3.4"):
    S.request_code(ddb, email, SMTP_OFF)
    code = _get_code(ddb, email)
    return S.register(ddb, email, code, nick, phone, ip)


# ---------- 验证码 ----------

def test_code_resend_cooldown(ddb):
    """60s 冷却内重发 → 429"""
    S.request_code(ddb, "a@x.com", SMTP_OFF)
    with pytest.raises(DiscussError) as e:
        S.request_code(ddb, "a@x.com", SMTP_OFF)
    assert e.value.status_code == 429


def test_code_wrong_attempts_invalidate(ddb):
    """5 次错误后作废"""
    S.request_code(ddb, "a@x.com", SMTP_OFF)
    _get_code(ddb, "a@x.com")
    for _ in range(5):
        with pytest.raises(DiscussError, match="验证码错误"):
            S.register(ddb, "a@x.com", "000000", "n", "1", "ip")
    # 第 6 次即使码对也已作废
    with pytest.raises(DiscussError) as e:
        S.register(ddb, "a@x.com", "123456", "n", "1", "ip")
    assert "失效" in e.value.message


# ---------- 注册 / 登录 ----------

def test_register_and_login_flow(ddb):
    user = _register(ddb)
    assert user.nickname == "小明"
    # 登录（重新请求验证码，绕过冷却：手动改 sent_at）
    rec_time = datetime.now() - timedelta(seconds=CODE_RESEND_SECONDS + 1)
    S.request_code.__wrapped__ if False else None
    code_rec = ddb.query(DiscussCode).filter(DiscussCode.email == "a@x.com").first()
    assert code_rec is None  # 注册已消费
    S.request_code(ddb, "a@x.com", SMTP_OFF)
    code = _get_code(ddb, "a@x.com")
    u2 = S.login(ddb, "a@x.com", code)
    assert u2.id == user.id


def test_register_duplicate_email(ddb):
    _register(ddb)
    S.request_code(ddb, "b@x.com", SMTP_OFF)  # 换邮箱拿码
    with pytest.raises(DiscussError) as e:
        S.register(ddb, "a@x.com", "123456", "n", "1", "ip")
    assert "已注册" in e.value.message


def test_register_ip_daily_limit(ddb):
    """单 IP 每日 ≤5 个新账号"""
    for i in range(5):
        _register(ddb, email=f"u{i}@x.com", ip="9.9.9.9")
    S.request_code(ddb, "u5@x.com", SMTP_OFF)
    code = _get_code(ddb, "u5@x.com")
    with pytest.raises(DiscussError) as e:
        S.register(ddb, "u5@x.com", code, "n", "1", "9.9.9.9")
    assert e.value.status_code == 429


# ---------- 发帖 / 楼结构 ----------

def test_post_thread_and_own_reply(ddb):
    user = _register(ddb)
    root = S.post_message(ddb, user, "第一条留言")
    assert root.thread_id == root.id and root.parent_id is None
    # 绕过 1 分钟限流
    root.created_at = datetime.now() - timedelta(seconds=POST_MIN_INTERVAL_SECONDS + 1)
    ddb.commit()
    extra = S.post_message(ddb, user, "补充内容", thread_id=root.id)
    assert extra.thread_id == root.id and extra.parent_id == root.id


def test_cannot_reply_in_others_thread(ddb):
    u1 = _register(ddb, email="a@x.com", ip="1.1.1.1")
    u2 = _register(ddb, email="b@x.com", ip="2.2.2.2")
    root = S.post_message(ddb, u1, "u1 的楼")
    with pytest.raises(DiscussError) as e:
        S.post_message(ddb, u2, "蹭楼", thread_id=root.id)
    assert e.value.status_code == 403


def test_post_rate_limit(ddb):
    user = _register(ddb)
    S.post_message(ddb, user, "第一条")
    with pytest.raises(DiscussError) as e:
        S.post_message(ddb, user, "太快了")
    assert e.value.status_code == 429


def test_media_count_limits(ddb):
    """单帖图片/视频数量按类型限额（防刷图刷视频）；限额内允许。"""
    user = _register(ddb)
    imgs = [{"type": "image", "url": f"/api/v1/discuss/media/{i}.jpg"} for i in range(10)]
    vids = [{"type": "video", "url": f"/api/v1/discuss/media/{i}.mp4"} for i in range(2)]
    with pytest.raises(DiscussError) as e:          # 10 张图 > 9
        S.post_message(ddb, user, "太多图", attachments=imgs)
    assert "图片" in e.value.message
    with pytest.raises(DiscussError) as e:          # 2 个视频 > 1
        S.post_message(ddb, user, "太多视频", attachments=vids)
    assert "视频" in e.value.message
    ok = S.post_message(ddb, user, "刚好", attachments=imgs[:9] + vids[:1])  # 9 图 + 1 视频
    assert len(ok.attachments) == 10


def test_user_only_sees_own_threads(ddb):
    """公开端按 ext_user_id 过滤：用户只看到自己的楼 + 官方回复，看不到他人内容。"""
    a = _register(ddb, email="a@x.com", ip="1.1.1.1")
    b = _register(ddb, email="b@x.com", ip="2.2.2.2")
    a_root = S.post_message(ddb, a, "A 的留言")
    S.post_message(ddb, b, "B 的留言")
    S.internal_reply(ddb, a_root.id, "客服小王", "A 你好，已收到")

    res_a = S.list_threads(ddb, include_hidden=False, ext_user_id=a.id)
    assert res_a["total"] == 1
    assert res_a["items"][0]["content"] == "A 的留言"
    assert any(r["author_type"] == "internal" for r in res_a["items"][0]["replies"])  # 官方回复可见

    res_b = S.list_threads(ddb, include_hidden=False, ext_user_id=b.id)
    assert res_b["total"] == 1 and res_b["items"][0]["content"] == "B 的留言"

    # 内部端不传 ext_user_id → 看到全部
    assert S.list_threads(ddb, include_hidden=True)["total"] == 2


def test_blocked_user_cannot_post(ddb):
    user = _register(ddb)
    S.set_user_blocked(ddb, user.id, True)
    with pytest.raises(DiscussError) as e:
        S.post_message(ddb, user, "hello")
    assert e.value.status_code == 403


# ---------- 内部动作 ----------

def test_internal_reply_marks_replied_and_unreplied_filter(ddb):
    user = _register(ddb)
    root = S.post_message(ddb, user, "求回复")
    # 未回复筛选命中
    r = S.list_threads(ddb, include_hidden=True, only_unreplied=True)
    assert r["total"] == 1
    S.internal_reply(ddb, root.id, "刘丹", "官方回复")
    r2 = S.list_threads(ddb, include_hidden=True, only_unreplied=True)
    assert r2["total"] == 0
    # 楼内含官方回复
    full = S.list_threads(ddb, include_hidden=True)
    assert full["items"][0]["replies"][0]["author_type"] == "internal"


def test_star_and_filter(ddb):
    user = _register(ddb)
    root = S.post_message(ddb, user, "有价值的建议")
    S.set_star(ddb, root.id, 4)
    r = S.list_threads(ddb, include_hidden=True, min_star=4)
    assert r["total"] == 1 and r["items"][0]["star"] == 4
    # 公开端也可见星级
    pub = S.list_threads(ddb, include_hidden=False)
    assert pub["items"][0]["star"] == 4


def test_hide_message_excluded_from_public(ddb):
    user = _register(ddb)
    root = S.post_message(ddb, user, "违规内容")
    S.set_visibility(ddb, root.id, False)
    assert S.list_threads(ddb, include_hidden=False)["total"] == 0
    assert S.list_threads(ddb, include_hidden=True)["total"] == 1


def test_public_view_has_no_privacy(ddb):
    """公开视图绝不含邮箱/手机号"""
    user = _register(ddb)
    S.post_message(ddb, user, "hello")
    pub = S.list_threads(ddb, include_hidden=False)
    item = pub["items"][0]
    assert "ext_email" not in item and "ext_phone" not in item
    # 内部视图含资料
    admin = S.list_threads(ddb, include_hidden=True)
    assert admin["items"][0]["ext_email"] == "a@x.com"


def test_search_by_content_and_phone(ddb):
    user = _register(ddb, phone="13912345678")
    S.post_message(ddb, user, "关于价格的建议")
    assert S.list_threads(ddb, include_hidden=True, keyword="价格")["total"] == 1
    assert S.list_threads(ddb, include_hidden=True, keyword="1391234")["total"] == 1
    assert S.list_threads(ddb, include_hidden=True, keyword="不存在")["total"] == 0


# ---------- 独立 JWT ----------

def test_ext_token_roundtrip_and_isolation():
    """外部 token 可验回；且内部 verify 不认外部 token（不同密钥+aud）"""
    token = create_ext_token(42)
    assert verify_ext_token(token) == 42
    assert verify_internal_token(token) is None       # 内部校验不认
    assert verify_ext_token("garbage") is None


def test_ensure_sqlite_dir_creates_missing_parent(tmp_path):
    """discuss 库路径父目录不存在时应自动创建（修复容器里 /discuss/board 500）。"""
    from backend.discuss.db import _ensure_sqlite_dir
    target = tmp_path / "nested" / "sub" / "discuss.db"
    assert not target.parent.exists()
    _ensure_sqlite_dir(f"sqlite:///{target.as_posix()}")
    assert target.parent.exists()          # 目录已建
    _ensure_sqlite_dir("sqlite:///:memory:")  # 内存库不涉及目录，不应报错


def test_send_email_verbose_surfaces_reason():
    """未配置 host → 降级成功；配置了但连接失败 → 返回真实原因（供测试邮件回显）"""
    ok, detail = S.send_email_verbose({"host": ""}, "a@b.com", "s", "b")
    assert ok is True and "SMTP" in detail
    # 指向无监听端口 → 快速失败，detail 携带具体异常（不再被吞成通用文案）
    ok, detail = S.send_email_verbose(
        {"host": "127.0.0.1", "port": 1, "ssl": False, "username": ""}, "a@b.com", "s", "b")
    assert ok is False and detail        # 非空原因


def test_send_email_transport_derived_from_port(monkeypatch):
    """传输按端口推导：465→隐式 SSL；587→明文+STARTTLS（对齐 BH，避免 SSL 勾选配错）。"""
    import backend.discuss.service as svc

    class _Fake:
        used = {}

        def __init__(self, host, port, timeout=10):
            _Fake.used["cls"] = type(self).__name__
            _Fake.used["starttls"] = False

        def __enter__(self): return self
        def __exit__(self, *a): return False
        def starttls(self): _Fake.used["starttls"] = True
        def login(self, u, p): pass
        def sendmail(self, *a): pass

    class _FakeSSL(_Fake): pass

    monkeypatch.setattr(svc.smtplib, "SMTP", _Fake)
    monkeypatch.setattr(svc.smtplib, "SMTP_SSL", _FakeSSL)

    # 465：走 SMTP_SSL，不调用 starttls
    _Fake.used = {}
    ok, _ = S.send_email_verbose({"host": "h", "port": 465, "ssl": False, "username": ""}, "a@b.com", "s", "b")
    assert ok is True and _Fake.used["cls"] == "_FakeSSL" and _Fake.used["starttls"] is False
    # 587 + ssl：走明文 SMTP + STARTTLS
    _Fake.used = {}
    ok, _ = S.send_email_verbose({"host": "h", "port": 587, "ssl": True, "username": ""}, "a@b.com", "s", "b")
    assert ok is True and _Fake.used["cls"] == "_Fake" and _Fake.used["starttls"] is True


def test_envelope_sender_always_valid_email(monkeypatch):
    """信封 MAIL FROM 恒用登录账号：发件人填成裸名字（walker）也不会当地址用，避免 500 bad syntax。"""
    import backend.discuss.service as svc
    captured = {}

    class _Fake:
        def __init__(self, host, port, timeout=10): pass
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def starttls(self): pass
        def login(self, u, p): pass
        def sendmail(self, envelope_from, to, data):
            captured["from"] = envelope_from

    monkeypatch.setattr(svc.smtplib, "SMTP_SSL", _Fake)
    monkeypatch.setattr(svc.smtplib, "SMTP", _Fake)

    # 发件人填的是名字 → 信封用登录账号，不是 "walker"
    ok, _ = S.send_email_verbose(
        {"host": "h", "port": 465, "username": "walker@youdoogo.com", "sender": "walker"},
        "to@x.com", "s", "b")
    assert ok is True and captured["from"] == "walker@youdoogo.com"

