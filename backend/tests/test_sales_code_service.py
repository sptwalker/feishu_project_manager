"""内部销售码服务测试"""
import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.db.base import Base
from backend.models.user import User, UserRole
from backend.models.sales_code import SalesCode, SalesCodePrefix  # noqa: F401 (create_all 需注册)
from backend.models.system_setting import SystemSetting  # noqa: F401 (create_all 需注册)
from backend.services.sales_code_service import SalesCodeService, DEFAULT_GEN_PASSWORD


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


def _mk_user(db, name="申华", role=UserRole.ADMIN):
    u = User(feishu_user_id=f"ou_{name}", name=name, role=role)
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _mk_prefix(db, admin, prefix="ABC", remark="", max_count=None):
    return SalesCodeService.create_prefix(db, prefix, remark, max_count, admin)


def _gen(db, count, issued_to, admin, prefix="ABC"):
    """测试便捷：确保前缀存在后生成。"""
    if not db.query(SalesCodePrefix).filter(SalesCodePrefix.prefix == prefix).first():
        _mk_prefix(db, admin, prefix)
    return SalesCodeService.generate_batch(db, count, issued_to, admin, prefix)


# ---- 前缀库 ----

def test_create_prefix_normalizes_and_unique(db_session):
    admin = _mk_user(db_session)
    p = _mk_prefix(db_session, admin, prefix=" abc ", remark="华东", max_count=100)
    assert p.prefix == "ABC"          # 去空白转大写
    assert p.remark == "华东"
    assert p.max_count == 100
    with pytest.raises(ValueError):   # 重复
        _mk_prefix(db_session, admin, prefix="ABC")


def test_create_prefix_rejects_bad_format(db_session):
    admin = _mk_user(db_session)
    for bad in ["", "TOOLONG12", "a-b", "有中文"]:
        with pytest.raises(ValueError):
            _mk_prefix(db_session, admin, prefix=bad)


def test_list_prefix_reports_used_and_remaining(db_session):
    admin = _mk_user(db_session)
    _mk_prefix(db_session, admin, prefix="LIM", max_count=10)
    SalesCodeService.generate_batch(db_session, 3, "x", admin, "LIM")
    row = next(p for p in SalesCodeService.list_prefixes(db_session) if p["prefix"] == "LIM")
    assert row["used"] == 3
    assert row["remaining"] == 7


# ---- 生成 ----

def test_generate_batch_count_unique_and_prefixed(db_session):
    admin = _mk_user(db_session)
    rows = _gen(db_session, 50, "华东渠道", admin, prefix="ABC")
    assert len(rows) == 50
    codes = {r.code for r in rows}
    assert len(codes) == 50  # 批内唯一
    assert all(r.code.startswith("ABC-") for r in rows)     # 前缀-随机
    assert all(len(r.code) == len("ABC-") + 8 for r in rows)
    assert all(r.prefix == "ABC" for r in rows)
    assert db_session.query(SalesCode).count() == 50
    assert all(r.generated_by == "申华" for r in rows)
    assert all(r.issued_to == "华东渠道" for r in rows)


def test_generate_batch_bounds(db_session):
    admin = _mk_user(db_session)
    _mk_prefix(db_session, admin, prefix="ABC")
    with pytest.raises(ValueError):
        SalesCodeService.generate_batch(db_session, 0, "x", admin, "ABC")
    with pytest.raises(ValueError):
        SalesCodeService.generate_batch(db_session, 1001, "x", admin, "ABC")


def test_generate_requires_known_enabled_prefix(db_session):
    admin = _mk_user(db_session)
    # 未入库前缀
    with pytest.raises(ValueError):
        SalesCodeService.generate_batch(db_session, 1, "x", admin, "NOPE")
    # 禁用后不可用
    p = _mk_prefix(db_session, admin, prefix="OFF")
    SalesCodeService.set_prefix_disabled(db_session, p.id, True)
    with pytest.raises(ValueError):
        SalesCodeService.generate_batch(db_session, 1, "x", admin, "OFF")


def test_generate_respects_limit(db_session):
    admin = _mk_user(db_session)
    _mk_prefix(db_session, admin, prefix="LIM", max_count=5)
    SalesCodeService.generate_batch(db_session, 3, "x", admin, "LIM")   # 已用 3
    with pytest.raises(ValueError) as ei:
        SalesCodeService.generate_batch(db_session, 5, "x", admin, "LIM")  # 剩 2，要 5 → 拒绝
    assert "剩余" in str(ei.value)
    # 剩余额度内可继续
    more = SalesCodeService.generate_batch(db_session, 2, "x", admin, "LIM")
    assert len(more) == 2
    assert SalesCodeService.count_by_prefix(db_session, "LIM") == 5


# ---- 逐条核销 ----

def test_redeem_success(db_session):
    admin = _mk_user(db_session)
    code = _gen(db_session, 1, "张三", admin)[0].code
    ok, reason, rec = SalesCodeService.redeem_one(db_session, code, admin)
    assert ok is True
    assert rec.redeemed is True
    assert rec.redeemed_by == "申华"
    assert rec.redeemed_at is not None


def test_redeem_not_found(db_session):
    admin = _mk_user(db_session)
    ok, reason, rec = SalesCodeService.redeem_one(db_session, "ABC-NOPE1234", admin)
    assert ok is False
    assert "不存在" in reason
    assert rec is None


def test_redeem_already(db_session):
    admin = _mk_user(db_session)
    code = _gen(db_session, 1, "张三", admin)[0].code
    SalesCodeService.redeem_one(db_session, code, admin)
    ok, reason, rec = SalesCodeService.redeem_one(db_session, code, admin)
    assert ok is False
    assert "核销" in reason  # "已于 ... 被 ... 核销"


# ---- 批量核销 ----

def test_redeem_batch_mixed(db_session):
    admin = _mk_user(db_session)
    rows = _gen(db_session, 3, "批量", admin)
    good = [r.code for r in rows]
    # 先核销一个，使其在批量里变成"已核销"失败项
    SalesCodeService.redeem_one(db_session, good[0], admin)
    # 输入：1 个已核销 + 2 个可核销 + 1 个不存在 + 空白/重复
    codes = [good[0], good[1], good[2], "ABC-GHOST99", "", good[1]]
    res = SalesCodeService.redeem_batch(db_session, codes, admin)
    redeemed_codes = {r.code for r in res["redeemed"]}
    failed_codes = {f["code"] for f in res["failed"]}
    assert redeemed_codes == {good[1], good[2]}          # 两个成功
    assert failed_codes == {good[0], "ABC-GHOST99"}      # 已核销 + 不存在；空白/重复被忽略


# ---- 查询 ----

def test_query_by_code_and_status(db_session):
    admin = _mk_user(db_session)
    rows = _gen(db_session, 5, "查询", admin)
    target = rows[0].code
    # 精确片段模糊命中
    hit = SalesCodeService.query(db_session, code=target[4:9])
    assert any(r.code == target for r in hit)
    # 按核销状态
    SalesCodeService.redeem_one(db_session, target, admin)
    assert len(SalesCodeService.query(db_session, redeemed=True)) == 1
    assert len(SalesCodeService.query(db_session, redeemed=False)) == 4


def test_query_by_prefix(db_session):
    admin = _mk_user(db_session)
    _gen(db_session, 3, "甲", admin, prefix="AAA")
    _gen(db_session, 2, "乙", admin, prefix="BBB")
    assert len(SalesCodeService.query(db_session, prefix="AAA")) == 3
    assert len(SalesCodeService.query(db_session, prefix="bbb")) == 2   # 大小写不敏感
    assert len(SalesCodeService.query(db_session)) == 5


def test_query_by_date_range(db_session):
    admin = _mk_user(db_session)
    _gen(db_session, 3, "日期", admin)
    today = datetime.now()
    # 覆盖今天 → 命中；未来窗口 → 不命中
    assert len(SalesCodeService.query(db_session, start=today - timedelta(days=1), end=today + timedelta(days=1))) == 3
    assert len(SalesCodeService.query(db_session, start=today + timedelta(days=1))) == 0


# ---- 二级密码 ----

def test_gen_password_default_then_change(db_session):
    # 初始：默认密码通过、其它拒绝
    assert SalesCodeService.is_gen_password_default(db_session) is True
    assert SalesCodeService.verify_gen_password(db_session, DEFAULT_GEN_PASSWORD) is True
    assert SalesCodeService.verify_gen_password(db_session, "wrong") is False
    # 改密后：旧默认失效、新密码通过、不再是默认
    SalesCodeService.set_gen_password(db_session, "newpass123")
    assert SalesCodeService.is_gen_password_default(db_session) is False
    assert SalesCodeService.verify_gen_password(db_session, DEFAULT_GEN_PASSWORD) is False
    assert SalesCodeService.verify_gen_password(db_session, "newpass123") is True


def test_set_gen_password_rejects_empty(db_session):
    with pytest.raises(ValueError):
        SalesCodeService.set_gen_password(db_session, "   ")
