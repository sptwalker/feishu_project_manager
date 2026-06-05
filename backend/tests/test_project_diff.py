"""项目字段变更描述 helper 单元测试"""
from datetime import date

from backend.models.project import Project, ProjectStatus, ProjectUrgency
from backend.services.project_diff import build_field_change_desc, _normalize, _fmt


def _proj(**kw):
    """构造一个内存 Project（不入库），带默认值。"""
    base = dict(
        name="A", content="", status=ProjectStatus.IN_PROGRESS, urgency=ProjectUrgency.MEDIUM,
        department=None, owner_name=None, related_name=None, completion=50,
        is_long_term=False, estimated_end_date=None, actual_end_date=None,
        record_date=date(2026, 6, 1),
    )
    base.update(kw)
    return Project(**base)


def test_completion_change():
    p = _proj(completion=50)
    desc = build_field_change_desc(p, {"completion": 100}, "A")
    assert desc == '修改了项目"A"：完成度 50%→100%'


def test_status_enum_change_to_cn():
    p = _proj(status=ProjectStatus.IN_PROGRESS)
    desc = build_field_change_desc(p, {"status": ProjectStatus.COMPLETED}, "A")
    assert desc == '修改了项目"A"：完成情况 进行中→已完成'


def test_urgency_change_cn():
    p = _proj(urgency=ProjectUrgency.MEDIUM)
    desc = build_field_change_desc(p, {"urgency": ProjectUrgency.URGENT}, "A")
    assert "优先级 中→重要" in desc


def test_multi_field_change():
    p = _proj(completion=50, status=ProjectStatus.IN_PROGRESS)
    desc = build_field_change_desc(p, {"completion": 80, "status": ProjectStatus.COMPLETED}, "A")
    assert "完成度 50%→80%" in desc and "完成情况 进行中→已完成" in desc


def test_none_to_value():
    p = _proj(owner_name=None)
    desc = build_field_change_desc(p, {"owner_name": "申华"}, "A")
    assert desc == '修改了项目"A"：负责人 空→申华'


def test_date_change():
    p = _proj(estimated_end_date=None)
    desc = build_field_change_desc(p, {"estimated_end_date": date(2026, 7, 1)}, "A")
    assert "截止日期 空→2026-07-01" in desc


def test_bool_change():
    p = _proj(is_long_term=False)
    desc = build_field_change_desc(p, {"is_long_term": True}, "A")
    assert "长期项目 否→是" in desc


def test_no_change_returns_none():
    p = _proj(completion=50)
    # 值没变 + None↔"" 归一 → 无变化
    assert build_field_change_desc(p, {"completion": 50}, "A") is None
    assert build_field_change_desc(p, {"department": None}, "A") is None  # None == None


def test_progress_log_field_ignored():
    p = _proj()
    # progress_log 不属于基本字段，应被跳过
    assert build_field_change_desc(p, {"progress_log": [{"x": 1}]}, "A") is None


def test_normalize_enum_equals_value():
    # 枚举成员与其字符串值归一后相等（避免误报）
    assert _normalize(ProjectStatus.COMPLETED) == _normalize("completed")
    assert _normalize(None) == _normalize("")
