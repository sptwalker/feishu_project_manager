"""项目字段变更描述 helper

对比项目编辑前的旧值与本次提交 payload，生成中文可读的字段级变更描述，
供「项目详情 › 历史修改记录」展示。纯函数、不依赖 db，便于单测。

只处理基本字段；progress_log 由 OperationLogService.classify_progress_change 单独分类。
枚举中文须与前端 labels.ts 一致。
"""
from datetime import date
from typing import Optional

from backend.models.project import ProjectStatus, ProjectUrgency

# 字段 → 中文标签（仅基本字段）
FIELD_LABELS = {
    "name": "项目名称",
    "content": "简要说明",
    "status": "完成情况",
    "urgency": "优先级",
    "department": "部门",
    "owner_name": "负责人",
    "related_name": "相关人",
    "completion": "完成度",
    "is_long_term": "长期项目",
    "estimated_end_date": "截止日期",
    "actual_end_date": "实际完成时间",
    "record_date": "记录日期",
}

# 枚举 → 中文（与前端 labels.ts 一致）
STATUS_CN = {
    "planned": "待启动",
    "in_progress": "进行中",
    "paused": "暂停",
    "completed": "已完成",
    "cancelled": "已取消",
}
URGENCY_CN = {
    "low": "低",
    "medium": "中",
    "high": "高",
    "urgent": "重要",
}


def _enum_value(val) -> Optional[str]:
    """取枚举成员的 value 字符串；普通值原样返回。"""
    if isinstance(val, (ProjectStatus, ProjectUrgency)):
        return val.value
    return val


def _normalize(val):
    """归一化用于判等：None/"" 视为等价；枚举取 value；date 取 isoformat。
    避免"提交了但值没变"产生噪音日志。"""
    if val is None or val == "":
        return None
    if isinstance(val, (ProjectStatus, ProjectUrgency)):
        return val.value
    if isinstance(val, date):
        return val.isoformat()
    return val


def _fmt(field: str, val) -> str:
    """把字段值格式化为中文可读字符串。"""
    if val is None or val == "":
        return "空"
    if field == "status":
        v = _enum_value(val)
        return STATUS_CN.get(v, str(v))
    if field == "urgency":
        v = _enum_value(val)
        return URGENCY_CN.get(v, str(v))
    if field == "completion":
        return f"{val}%"
    if field == "is_long_term":
        return "是" if val else "否"
    if isinstance(val, date):
        return val.isoformat()
    s = str(val)
    return s if len(s) <= 20 else s[:20] + "…"


def build_field_change_desc(project, payload: dict, project_name: str) -> Optional[str]:
    """对比基本字段，返回中文变更描述。无字段变化返回 None。

    示例：'修改了项目"X"：完成度 50%→100%，完成情况 进行中→已完成'
    project：编辑前的 ORM 对象（取旧值）；payload：本次提交字段(exclude_unset)。
    """
    parts = []
    for field, new_val in payload.items():
        if field not in FIELD_LABELS:
            continue  # 跳过 progress_log 等非基本字段
        old_val = getattr(project, field, None)
        if _normalize(old_val) == _normalize(new_val):
            continue  # 值未变，不记
        parts.append(f"{FIELD_LABELS[field]} {_fmt(field, old_val)}→{_fmt(field, new_val)}")
    if not parts:
        return None
    return f'修改了项目"{project_name}"：' + "，".join(parts)
