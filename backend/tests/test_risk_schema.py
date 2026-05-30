import pytest
from pydantic import ValidationError
from backend.schemas.risk import RiskCreate, RiskUpdate
from backend.models.risk import RiskStatus


def test_risk_create_minimal_valid():
    """最小合法入参可创建 RiskCreate"""
    risk = RiskCreate(title="风险A")
    assert risk.title == "风险A"
    assert risk.status == RiskStatus.OPEN
    assert risk.owner_id is None


def test_risk_create_full_valid():
    """完整入参可创建 RiskCreate"""
    risk = RiskCreate(
        title="风险B",
        description="描述",
        status=RiskStatus.MONITORING,
        owner_id=3,
    )
    assert risk.status == RiskStatus.MONITORING
    assert risk.owner_id == 3


def test_risk_title_required():
    """title 缺失应校验失败"""
    with pytest.raises(ValidationError):
        RiskCreate(description="无标题")


def test_risk_title_empty_invalid():
    """title 为空字符串应校验失败"""
    with pytest.raises(ValidationError):
        RiskCreate(title="")


def test_risk_owner_id_must_be_positive():
    """owner_id 若提供必须为正数"""
    with pytest.raises(ValidationError):
        RiskCreate(title="风险", owner_id=0)


def test_risk_update_all_optional():
    """RiskUpdate 所有字段可选，空入参合法"""
    update = RiskUpdate()
    assert update.model_dump(exclude_unset=True) == {}


def test_risk_update_partial():
    """RiskUpdate 部分字段更新"""
    update = RiskUpdate(status=RiskStatus.RESOLVED)
    data = update.model_dump(exclude_unset=True)
    assert data == {"status": RiskStatus.RESOLVED}
