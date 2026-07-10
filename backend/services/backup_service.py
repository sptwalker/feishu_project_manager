"""数据库全量导出 / 导入服务（JSON 快照，全量替换）。

导出：全部业务表（见 EXPORT_ORDER）序列化为 JSON 快照（不含 alembic_version）。
导入：事务内按 FK 依赖逆序清空、正序插入，失败整体回滚。老快照缺少后加入的表
（OPTIONAL_TABLES）时跳过该表、保持现有数据不动，保证向后兼容。
"""
from datetime import date, datetime
from typing import Any
import enum

from sqlalchemy import inspect as sa_inspect
from sqlalchemy import Date, DateTime, Enum as SAEnum
from sqlalchemy.orm import Session

from backend.models.user import User
from backend.models.department import Department
from backend.models.project import Project
from backend.models.task import Task
from backend.models.risk import Risk
from backend.models.event import Event
from backend.models.system_setting import SystemSetting
from backend.models.meeting_record import MeetingRecord
from backend.models.operation_log import OperationLog
from backend.models.sales_code import SalesCode, SalesCodePrefix

SNAPSHOT_VERSION = 1

# 插入顺序（满足外键依赖）；删除时逆序
EXPORT_ORDER: list[tuple[str, type]] = [
    ("users", User),
    ("departments", Department),
    ("system_settings", SystemSetting),
    ("projects", Project),
    ("tasks", Task),
    ("risks", Risk),
    ("events", Event),
    ("meeting_records", MeetingRecord),
    ("operation_logs", OperationLog),
    ("sales_code_prefixes", SalesCodePrefix),
    ("sales_codes", SalesCode),
]

# 后加入的表：老快照（此功能之前导出的）可能不含这些键。导入时视为「缺省=不动」，
# 保证旧快照仍可导入且不会误删现有销售码数据；新快照含这些键时照常全量替换。
OPTIONAL_TABLES = {"sales_code_prefixes", "sales_codes"}


def _serialize_value(value: Any) -> Any:
    """把列值转为 JSON 可序列化形式"""
    if isinstance(value, enum.Enum):
        return value.value
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


def _row_to_dict(obj: Any) -> dict:
    cols = sa_inspect(obj.__class__).columns.keys()
    return {c: _serialize_value(getattr(obj, c)) for c in cols}


def _coerce_value(col_type: Any, value: Any) -> Any:
    """把 JSON 中的原始值还原为列所需的 Python 类型（枚举/日期/时间）"""
    if value is None:
        return None
    if isinstance(col_type, SAEnum) and getattr(col_type, "enum_class", None) is not None:
        # 按枚举 value 还原成成员（与导出的 .value 对应）
        return col_type.enum_class(value)
    if isinstance(col_type, DateTime):
        return datetime.fromisoformat(value) if isinstance(value, str) else value
    if isinstance(col_type, Date):
        return date.fromisoformat(value) if isinstance(value, str) else value
    return value


class BackupService:
    """数据库备份服务"""

    @staticmethod
    def export_all(db: Session, app_version: str = "1.0.0", now: datetime | None = None) -> dict:
        """导出全部业务表为 JSON 快照结构"""
        tables: dict[str, list[dict]] = {}
        for name, model in EXPORT_ORDER:
            rows = db.query(model).all()
            tables[name] = [_row_to_dict(r) for r in rows]
        return {
            "version": SNAPSHOT_VERSION,
            "exported_at": (now or datetime.now()).isoformat(),
            "app_version": app_version,
            "tables": tables,
        }

    @staticmethod
    def import_all(db: Session, payload: dict) -> dict[str, int]:
        """全量替换导入：事务内先删后插，失败回滚。返回各表导入行数。"""
        if not isinstance(payload, dict):
            raise ValueError("快照格式错误：根节点应为对象")
        if payload.get("version") != SNAPSHOT_VERSION:
            raise ValueError(
                f"快照版本不兼容：期望 {SNAPSHOT_VERSION}，实际 {payload.get('version')}"
            )
        tables = payload.get("tables")
        if not isinstance(tables, dict):
            raise ValueError("快照格式错误：缺少 tables")
        for name, _ in EXPORT_ORDER:
            if name not in tables:
                if name in OPTIONAL_TABLES:
                    continue  # 老快照无此表：跳过校验，导入时保持现有数据不动
                raise ValueError(f"快照缺少表数据或格式错误：{name}")
            if not isinstance(tables[name], list):
                raise ValueError(f"快照缺少表数据或格式错误：{name}")

        counts: dict[str, int] = {}
        try:
            # 逆序删除（先删子表）；仅删除快照包含的表，老快照未含的表保持不动
            for name, model in reversed(EXPORT_ORDER):
                if name in tables:
                    db.query(model).delete()
            # 正序插入
            for name, model in EXPORT_ORDER:
                if name not in tables:
                    continue
                columns = sa_inspect(model).columns
                col_keys = set(columns.keys())
                rows = tables[name]
                for raw in rows:
                    data = {
                        k: _coerce_value(columns[k].type, v)
                        for k, v in raw.items() if k in col_keys
                    }
                    db.add(model(**data))
                counts[name] = len(rows)
            db.commit()
        except Exception:
            db.rollback()
            raise
        return counts
