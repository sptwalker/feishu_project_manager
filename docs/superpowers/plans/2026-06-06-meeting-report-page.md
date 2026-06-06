# 周例会汇报页 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 新增一个全屏「周例会汇报页」，按部门→个人顺序逐一汇报待启动/进行中/暂停项目，支持拖拽排序、双计时与超时提示、项目进展全字段实时编辑。

**Architecture:** 前端为主（Vue3 + Pinia 新页面 + store），复用现有 `projectApi.update` 实时编辑；把 `ProjectDetailDrawer` 拆成「壳 + `ProjectDetailContent`」供抽屉和会议页共用。后端少量改动：`meeting_records` 加 `started_at/ended_at` 两列、新增"汇报顺序/计时设置"的 `SystemSetting` 接口、新增 `start-report` 端点、`archive_meeting` 补写 `ended_at`、开/关会议写操作日志。计时纯前端运行时不入库。

**Tech Stack:** 后端 FastAPI + SQLAlchemy + Alembic + pytest（SQLite，迁移用 `batch_alter_table`）；前端 Vue 3 + TypeScript + Vite + Element Plus + Pinia（无前端测试框架，靠 `vue-tsc` 类型检查 + 手工验证）。

**关键既有事实（调研确认）：**
- Alembic 当前 head revision = `d0e1f2a3b4c5`；新迁移 `down_revision` 写它。
- `MeetingRecord`/`SystemSetting` 的 `id/created_at/updated_at` 由 `BaseModel` 提供；`meeting_record.py` 当前仅 import `Date`，加时刻列需引入 `DateTime`。
- `ended_at` 真正落点是 `archive_meeting`（被 `close_meeting` 调用），不是 `close_meeting` 本身。
- `meeting_record_service.py` 顶部已 `from datetime import date, datetime`。
- 后端测试**无 conftest.py**，fixture 内联在每个测试文件（`db_session/_make_user/_client/_cleanup`）；403 由真实 `get_current_admin` 校验 `current_user.role` 产生，测试只覆写 `get_current_user`。
- `ProjectDetailDrawer.vue` 共 1232 行；对外契约：5 个 props（`visible/project/departments/owners/createMode`）+ 2 个 emit（`update:visible/updated`），被 `ProjectOverviewView`、`ProjectBoardView` 使用，重构后必须保持不变。
- 前端**无测试框架**（无 vitest/jest/spec 文件）。

---

## 阶段总览

- **阶段 A（后端模型与迁移）**：Task 1–2
- **阶段 B（后端设置 API）**：Task 3–5
- **阶段 C（后端会议起止与日志）**：Task 6–7
- **阶段 D（前端类型与 API 客户端）**：Task 8
- **阶段 E（抽屉重构：壳 + 内容组件）**：Task 9–10 ⚠️ 最高回归风险
- **阶段 F（前端 store）**：Task 11
- **阶段 G（前端组件与页面）**：Task 12–15
- **阶段 H（视觉打磨与端到端验证）**：Task 16–17

每个后端任务走 TDD（先写失败测试）。前端任务无单测，用 `cd frontend && npx vue-tsc --noEmit` 类型检查 + 手工验证替代。**每个 Task 末尾提交一次**（用户要求全部完成后才最终汇总，但过程中按计划逐任务 commit 到工作分支，便于回滚；不 push）。

---

## 阶段 A：后端模型与迁移

### Task 1: MeetingRecord 加 started_at / ended_at 两列

**Files:**
- Modify: `backend/models/meeting_record.py`
- Test: `backend/tests/test_meeting_report_api.py`（新建，本任务先建文件+第一个测试）

- [ ] **Step 1: 写失败测试**

新建 `backend/tests/test_meeting_report_api.py`，内联 fixture（仿 `test_settings_api.py`）并测试模型新列存在：

```python
"""周会汇报页相关 API 测试（起止时间 / 汇报顺序 / 计时设置）。
本项目无 conftest.py，fixture 内联。"""
import pytest
from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from backend.main import app
from backend.db.base import Base
from backend.api.deps import get_db
from backend.core.dependencies import get_current_user
from backend.models.user import User, UserRole
from backend.models.meeting_record import MeetingRecord


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


def _make_user(db, feishu_id, role=UserRole.MEMBER):
    user = User(feishu_user_id=feishu_id, name=feishu_id, role=role)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _client(db_session, current_user):
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_current_user] = lambda: current_user
    return TestClient(app)


def _cleanup():
    app.dependency_overrides.clear()


def test_meeting_record_has_started_and_ended_columns(db_session):
    """MeetingRecord 应有 started_at / ended_at 两列，默认 None。"""
    rec = MeetingRecord(session=99, meeting_date=date(2026, 6, 6), status="active")
    db_session.add(rec)
    db_session.commit()
    db_session.refresh(rec)
    assert rec.started_at is None
    assert rec.ended_at is None
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && python -m pytest tests/test_meeting_report_api.py::test_meeting_record_has_started_and_ended_columns -v`
Expected: FAIL —`AttributeError`/`TypeError`（无 started_at 列）。

- [ ] **Step 3: 给模型加列**

编辑 `backend/models/meeting_record.py`：第 1 行 import 增加 `DateTime`；在 `created_by` 列之后新增两列。

把第 1 行：
```python
from sqlalchemy import Column, Integer, String, Date, JSON
```
改为：
```python
from sqlalchemy import Column, Integer, String, Date, DateTime, JSON
```

在 `created_by = Column(...)` 那一行之后新增：
```python
    started_at = Column(DateTime, nullable=True, comment="汇报会议开始时刻（首次进入汇报模式时写入）")
    ended_at = Column(DateTime, nullable=True, comment="汇报会议结束时刻（归档时写入）")
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd backend && python -m pytest tests/test_meeting_report_api.py::test_meeting_record_has_started_and_ended_columns -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add backend/models/meeting_record.py backend/tests/test_meeting_report_api.py
git commit -m "feat(backend): MeetingRecord 增加 started_at/ended_at 列"
```

---

### Task 2: Alembic 迁移（给 meeting_records 加两列）

**Files:**
- Create: `backend/alembic/versions/e1f2a3b4c5d6_add_meeting_timing_columns.py`

- [ ] **Step 1: 新建迁移文件**

新建 `backend/alembic/versions/e1f2a3b4c5d6_add_meeting_timing_columns.py`（SQLite 用 `batch_alter_table`）：

```python
"""add started_at/ended_at to meeting_records

Revision ID: e1f2a3b4c5d6
Revises: d0e1f2a3b4c5
Create Date: 2026-06-06 10:00:00.000000

给周会记录表加 started_at/ended_at（均可空，DateTime），
记录汇报会议的实际开始/结束时刻。旧记录两列为 NULL。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'e1f2a3b4c5d6'
down_revision: Union[str, Sequence[str], None] = 'd0e1f2a3b4c5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('meeting_records', schema=None) as batch_op:
        batch_op.add_column(sa.Column('started_at', sa.DateTime(), nullable=True,
                                      comment='汇报会议开始时刻'))
        batch_op.add_column(sa.Column('ended_at', sa.DateTime(), nullable=True,
                                      comment='汇报会议结束时刻'))


def downgrade() -> None:
    with op.batch_alter_table('meeting_records', schema=None) as batch_op:
        batch_op.drop_column('ended_at')
        batch_op.drop_column('started_at')
```

- [ ] **Step 2: 验证迁移链与可升级**

Run: `cd backend && python -m alembic heads`
Expected: 输出包含 `e1f2a3b4c5d6 (head)`，且只有一个 head（无分叉）。

Run: `cd backend && python -m alembic upgrade head`
Expected: 成功执行到 `e1f2a3b4c5d6`，无报错。

Run: `cd backend && python -m alembic downgrade -1 && python -m alembic upgrade head`
Expected: 回滚一步再升级成功（验证 downgrade 可逆）。

- [ ] **Step 3: 提交**

```bash
git add backend/alembic/versions/e1f2a3b4c5d6_add_meeting_timing_columns.py
git commit -m "feat(backend): 迁移 meeting_records 加 started_at/ended_at"
```

---

## 阶段 B：后端设置 API（汇报顺序 + 计时设置）

### Task 3: SettingsService 增加汇报顺序/计时设置读写方法

**Files:**
- Modify: `backend/services/settings_service.py`
- Test: `backend/tests/test_meeting_report_api.py`

- [ ] **Step 1: 写失败测试**

在 `backend/tests/test_meeting_report_api.py` 末尾追加：

```python
from backend.services.settings_service import SettingsService


def test_report_order_default_empty(db_session):
    """未设置时，汇报顺序默认空结构。"""
    order = SettingsService.get_meeting_report_order(db_session)
    assert order == {"departments": [], "members": {}}


def test_report_order_roundtrip(db_session):
    """写入后读回一致（含中文不转义）。"""
    SettingsService.set_meeting_report_order(
        db_session,
        departments=["研发部", "市场部"],
        members={"研发部": ["张三", "李四"], "市场部": ["王五"]},
    )
    order = SettingsService.get_meeting_report_order(db_session)
    assert order["departments"] == ["研发部", "市场部"]
    assert order["members"]["研发部"] == ["张三", "李四"]


def test_timer_settings_defaults_and_roundtrip(db_session):
    """计时设置默认 30/5，写入后读回。"""
    assert SettingsService.get_meeting_total_minutes(db_session) == 30
    assert SettingsService.get_meeting_person_threshold_minutes(db_session) == 5
    SettingsService.set_meeting_total_minutes(db_session, 45)
    SettingsService.set_meeting_person_threshold_minutes(db_session, 8)
    assert SettingsService.get_meeting_total_minutes(db_session) == 45
    assert SettingsService.get_meeting_person_threshold_minutes(db_session) == 8
```

- [ ] **Step 2: 运行确认失败**

Run: `cd backend && python -m pytest tests/test_meeting_report_api.py -k "report_order or timer_settings" -v`
Expected: FAIL（方法不存在）。

- [ ] **Step 3: 实现 service 方法**

编辑 `backend/services/settings_service.py`：

(a) 文件顶部 import 区增加（若尚无 `import json`）：
```python
import json
```

(b) 在已有 KEY 常量区（`AUTO_REMINDER_ENABLED_KEY` 那一组附近）新增：
```python
MEETING_REPORT_ORDER_KEY = "meeting_report_order"
MEETING_TOTAL_MINUTES_KEY = "meeting_total_minutes"
MEETING_PERSON_THRESHOLD_MINUTES_KEY = "meeting_person_threshold_minutes"
DEFAULT_MEETING_TOTAL_MINUTES = 30
DEFAULT_MEETING_PERSON_THRESHOLD_MINUTES = 5
```

(c) 在 `SettingsService` 类内（紧挨 `set_auto_reminder_enabled` 之后）新增方法：
```python
    # ---------- 周会汇报页：顺序 + 计时设置 ----------

    @staticmethod
    def get_meeting_report_order(db: Session) -> dict:
        """读取汇报顺序：{departments:[...], members:{部门:[人,...]}}。未设置/损坏返回空结构。"""
        raw = SettingsService.get_setting(db, MEETING_REPORT_ORDER_KEY, "")
        if not raw:
            return {"departments": [], "members": {}}
        try:
            data = json.loads(raw)
        except (ValueError, TypeError):
            return {"departments": [], "members": {}}
        return {
            "departments": data.get("departments") or [],
            "members": data.get("members") or {},
        }

    @staticmethod
    def set_meeting_report_order(db: Session, departments: list, members: dict) -> None:
        """保存汇报顺序（部门级 + 个人级）。中文不转义。"""
        SettingsService.set_setting(
            db,
            MEETING_REPORT_ORDER_KEY,
            json.dumps({"departments": departments, "members": members}, ensure_ascii=False),
        )

    @staticmethod
    def get_meeting_total_minutes(db: Session) -> int:
        """总会议时长（分钟），默认 30。"""
        return int(SettingsService.get_setting(
            db, MEETING_TOTAL_MINUTES_KEY, str(DEFAULT_MEETING_TOTAL_MINUTES)))

    @staticmethod
    def set_meeting_total_minutes(db: Session, minutes: int) -> None:
        SettingsService.set_setting(db, MEETING_TOTAL_MINUTES_KEY, str(minutes))

    @staticmethod
    def get_meeting_person_threshold_minutes(db: Session) -> int:
        """单人汇报提醒阈值（分钟），默认 5。"""
        return int(SettingsService.get_setting(
            db, MEETING_PERSON_THRESHOLD_MINUTES_KEY,
            str(DEFAULT_MEETING_PERSON_THRESHOLD_MINUTES)))

    @staticmethod
    def set_meeting_person_threshold_minutes(db: Session, minutes: int) -> None:
        SettingsService.set_setting(db, MEETING_PERSON_THRESHOLD_MINUTES_KEY, str(minutes))
```

- [ ] **Step 4: 运行确认通过**

Run: `cd backend && python -m pytest tests/test_meeting_report_api.py -k "report_order or timer_settings" -v`
Expected: PASS（3 passed）。

- [ ] **Step 5: 提交**

```bash
git add backend/services/settings_service.py backend/tests/test_meeting_report_api.py
git commit -m "feat(backend): SettingsService 增加汇报顺序与计时设置读写"
```

---

### Task 4: 设置 schema（汇报顺序 + 计时）

**Files:**
- Modify: `backend/schemas/setting.py`

- [ ] **Step 1: 新增 schema 类**

在 `backend/schemas/setting.py` 末尾追加（文件已 `from pydantic import BaseModel, Field`）：

```python
class MeetingReportOrderResponse(BaseModel):
    """周会汇报顺序（部门级 + 个人级）"""
    departments: list[str] = Field(default_factory=list, description="部门汇报顺序")
    members: dict[str, list[str]] = Field(default_factory=dict, description="各部门内个人顺序")


class MeetingReportOrderUpdate(BaseModel):
    """更新周会汇报顺序"""
    departments: list[str] = Field(default_factory=list)
    members: dict[str, list[str]] = Field(default_factory=dict)


class MeetingTimerResponse(BaseModel):
    """周会计时设置"""
    total_minutes: int = Field(30, ge=1, le=600, description="总会议时长（分钟）")
    person_threshold_minutes: int = Field(5, ge=1, le=120, description="单人提醒阈值（分钟）")


class MeetingTimerUpdate(BaseModel):
    """更新周会计时设置"""
    total_minutes: int = Field(..., ge=1, le=600)
    person_threshold_minutes: int = Field(..., ge=1, le=120)
```

- [ ] **Step 2: 类型检查（import 无误）**

Run: `cd backend && python -c "from backend.schemas.setting import MeetingReportOrderResponse, MeetingReportOrderUpdate, MeetingTimerResponse, MeetingTimerUpdate; print('ok')"`
Expected: 输出 `ok`

- [ ] **Step 3: 提交**

```bash
git add backend/schemas/setting.py
git commit -m "feat(backend): 新增汇报顺序/计时设置 schema"
```

---

### Task 5: 设置 API 端点（GET/PUT 汇报顺序 + 计时）

**Files:**
- Modify: `backend/api/v1/settings.py`
- Test: `backend/tests/test_meeting_report_api.py`

- [ ] **Step 1: 写失败测试**

在 `backend/tests/test_meeting_report_api.py` 末尾追加：

```python
def test_get_report_order_default_any_user(db_session):
    member = _make_user(db_session, "m1")
    client = _client(db_session, member)
    try:
        r = client.get("/api/v1/settings/meeting-report-order")
        assert r.status_code == 200
        assert r.json() == {"departments": [], "members": {}}
    finally:
        _cleanup()


def test_put_report_order_admin_then_get(db_session):
    admin = _make_user(db_session, "a1", role=UserRole.ADMIN)
    client = _client(db_session, admin)
    try:
        payload = {"departments": ["研发部"], "members": {"研发部": ["张三", "李四"]}}
        r = client.put("/api/v1/settings/meeting-report-order", json=payload)
        assert r.status_code == 200
        assert r.json()["departments"] == ["研发部"]
        r2 = client.get("/api/v1/settings/meeting-report-order")
        assert r2.json()["members"]["研发部"] == ["张三", "李四"]
    finally:
        _cleanup()


def test_put_report_order_non_admin_403(db_session):
    member = _make_user(db_session, "m2")
    client = _client(db_session, member)
    try:
        r = client.put("/api/v1/settings/meeting-report-order",
                       json={"departments": [], "members": {}})
        assert r.status_code == 403
    finally:
        _cleanup()


def test_timer_get_defaults_then_put(db_session):
    admin = _make_user(db_session, "a2", role=UserRole.ADMIN)
    client = _client(db_session, admin)
    try:
        r = client.get("/api/v1/settings/meeting-timer")
        assert r.json() == {"total_minutes": 30, "person_threshold_minutes": 5}
        r2 = client.put("/api/v1/settings/meeting-timer",
                        json={"total_minutes": 45, "person_threshold_minutes": 8})
        assert r2.status_code == 200
        assert r2.json()["total_minutes"] == 45
        assert client.get("/api/v1/settings/meeting-timer").json()["person_threshold_minutes"] == 8
    finally:
        _cleanup()


def test_timer_put_validation_rejects_zero(db_session):
    admin = _make_user(db_session, "a3", role=UserRole.ADMIN)
    client = _client(db_session, admin)
    try:
        r = client.put("/api/v1/settings/meeting-timer",
                       json={"total_minutes": 0, "person_threshold_minutes": 5})
        assert r.status_code == 422
    finally:
        _cleanup()
```

- [ ] **Step 2: 运行确认失败**

Run: `cd backend && python -m pytest tests/test_meeting_report_api.py -k "report_order or timer" -v`
Expected: FAIL（404，端点不存在）。

- [ ] **Step 3: 实现端点**

编辑 `backend/api/v1/settings.py`：

(a) 顶部 import 区（现有 schema import 块）追加：
```python
from backend.schemas.setting import (
    MeetingReportOrderResponse, MeetingReportOrderUpdate,
    MeetingTimerResponse, MeetingTimerUpdate,
)
```

(b) 文件末尾追加 4 个端点：
```python
@router.get("/settings/meeting-report-order", response_model=MeetingReportOrderResponse)
def get_meeting_report_order(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取周会汇报顺序（所有登录用户可读，用于正确排序）"""
    return MeetingReportOrderResponse(**SettingsService.get_meeting_report_order(db))


@router.put("/settings/meeting-report-order", response_model=MeetingReportOrderResponse)
def set_meeting_report_order(
    payload: MeetingReportOrderUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    """保存周会汇报顺序（仅管理员；拖拽结束即保存）"""
    SettingsService.set_meeting_report_order(db, payload.departments, payload.members)
    return MeetingReportOrderResponse(**SettingsService.get_meeting_report_order(db))


@router.get("/settings/meeting-timer", response_model=MeetingTimerResponse)
def get_meeting_timer(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取周会计时设置（所有登录用户可读）"""
    return MeetingTimerResponse(
        total_minutes=SettingsService.get_meeting_total_minutes(db),
        person_threshold_minutes=SettingsService.get_meeting_person_threshold_minutes(db),
    )


@router.put("/settings/meeting-timer", response_model=MeetingTimerResponse)
def set_meeting_timer(
    payload: MeetingTimerUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    """更新周会计时设置（仅管理员）"""
    SettingsService.set_meeting_total_minutes(db, payload.total_minutes)
    SettingsService.set_meeting_person_threshold_minutes(db, payload.person_threshold_minutes)
    return MeetingTimerResponse(
        total_minutes=SettingsService.get_meeting_total_minutes(db),
        person_threshold_minutes=SettingsService.get_meeting_person_threshold_minutes(db),
    )
```

- [ ] **Step 4: 运行确认通过**

Run: `cd backend && python -m pytest tests/test_meeting_report_api.py -k "report_order or timer" -v`
Expected: PASS（5 passed）。

- [ ] **Step 5: 提交**

```bash
git add backend/api/v1/settings.py backend/tests/test_meeting_report_api.py
git commit -m "feat(backend): 新增汇报顺序/计时设置 GET/PUT 端点"
```

---

## 阶段 C：后端会议起止时间与日志

### Task 6: archive_meeting 写 ended_at + start_report 写 started_at

**Files:**
- Modify: `backend/services/meeting_record_service.py`
- Test: `backend/tests/test_meeting_report_api.py`

- [ ] **Step 1: 写失败测试**

在 `backend/tests/test_meeting_report_api.py` 末尾追加：

```python
from backend.services.meeting_record_service import MeetingRecordService


def test_start_report_sets_started_at_idempotent(db_session):
    """start_report 首次写 started_at，重复调用不覆盖。"""
    rec = MeetingRecord(session=10, meeting_date=date(2026, 6, 6), status="active")
    db_session.add(rec)
    db_session.commit()

    MeetingRecordService.start_report(db_session, 10)
    db_session.refresh(rec)
    first = rec.started_at
    assert first is not None

    MeetingRecordService.start_report(db_session, 10)
    db_session.refresh(rec)
    assert rec.started_at == first  # 不被覆盖


def test_archive_sets_ended_at(db_session):
    """归档时写 ended_at。"""
    rec = MeetingRecord(session=11, meeting_date=date(2026, 6, 6), status="active")
    db_session.add(rec)
    db_session.commit()

    MeetingRecordService.archive_meeting(db_session, 11)
    db_session.refresh(rec)
    assert rec.status == "archived"
    assert rec.ended_at is not None
```

- [ ] **Step 2: 运行确认失败**

Run: `cd backend && python -m pytest tests/test_meeting_report_api.py -k "started_at or ended_at" -v`
Expected: FAIL（`start_report` 不存在 / `ended_at` 为 None）。

- [ ] **Step 3: 实现**

编辑 `backend/services/meeting_record_service.py`：

(a) 在 `archive_meeting` 里，`rec.status = "archived"` 那一行之后增加 `rec.ended_at = datetime.now()`；create-new 分支的 `MeetingRecord(...)` 调用里也加 `ended_at=datetime.now()`。改动后该方法相关片段为：
```python
        rec = MeetingRecordService._get_record(db, session)
        if rec:
            rec.content_snapshot = snapshot
            rec.status = "archived"
            rec.ended_at = datetime.now()
        else:
            rec = MeetingRecord(
                session=session,
                meeting_date=date.today(),
                status="archived",
                content_snapshot=snapshot,
                ended_at=datetime.now(),
            )
            db.add(rec)
```

(b) 在 `open_meeting` 方法之后（或类内任意合适位置）新增 `start_report`：
```python
    @staticmethod
    def start_report(db: Session, session: int) -> Optional[MeetingRecord]:
        """记录某次周会汇报开始时刻（仅首次写入，幂等）。无该 session 记录返回 None。"""
        rec = MeetingRecordService._get_record(db, session)
        if rec is None:
            return None
        if rec.started_at is None:
            rec.started_at = datetime.now()
            try:
                db.commit()
                db.refresh(rec)
            except Exception:
                db.rollback()
                raise
        return rec
```
（`Optional` 已在该文件 typing import 中；`datetime` 已 import。）

- [ ] **Step 4: 运行确认通过**

Run: `cd backend && python -m pytest tests/test_meeting_report_api.py -k "started_at or ended_at" -v`
Expected: PASS（2 passed）。

- [ ] **Step 5: 回归既有周会测试**

Run: `cd backend && python -m pytest tests/test_meeting_record.py -v`
Expected: 全 PASS（archive/close 行为未破坏）。

- [ ] **Step 6: 提交**

```bash
git add backend/services/meeting_record_service.py backend/tests/test_meeting_report_api.py
git commit -m "feat(backend): archive 写 ended_at、新增 start_report 写 started_at"
```

---

### Task 7: start-report 端点 + 开/关会议写操作日志

**Files:**
- Modify: `backend/api/v1/meeting_records.py`
- Test: `backend/tests/test_meeting_report_api.py`

- [ ] **Step 1: 写失败测试**

在 `backend/tests/test_meeting_report_api.py` 末尾追加：

```python
from backend.models.operation_log import OperationLog


def test_start_report_endpoint_admin(db_session):
    """管理员调用 start-report → 200，且写一条操作日志。"""
    admin = _make_user(db_session, "a4", role=UserRole.ADMIN)
    rec = MeetingRecord(session=20, meeting_date=date(2026, 6, 6), status="active")
    db_session.add(rec)
    db_session.commit()
    client = _client(db_session, admin)
    try:
        r = client.post("/api/v1/meeting-records/20/start-report")
        assert r.status_code == 200
        db_session.refresh(rec)
        assert rec.started_at is not None
        logs = db_session.query(OperationLog).filter(
            OperationLog.action == "meeting_report_start").all()
        assert len(logs) == 1
    finally:
        _cleanup()


def test_start_report_endpoint_non_admin_403(db_session):
    member = _make_user(db_session, "m4")
    rec = MeetingRecord(session=21, meeting_date=date(2026, 6, 6), status="active")
    db_session.add(rec)
    db_session.commit()
    client = _client(db_session, member)
    try:
        r = client.post("/api/v1/meeting-records/21/start-report")
        assert r.status_code == 403
    finally:
        _cleanup()


def test_close_meeting_writes_end_log(db_session):
    """关闭周会写 meeting_report_end 日志。"""
    admin = _make_user(db_session, "a5", role=UserRole.ADMIN)
    rec = MeetingRecord(session=22, meeting_date=date(2026, 6, 6), status="active")
    db_session.add(rec)
    db_session.commit()
    client = _client(db_session, admin)
    try:
        r = client.post("/api/v1/meeting-records/close")
        assert r.status_code == 200
        logs = db_session.query(OperationLog).filter(
            OperationLog.action == "meeting_report_end").all()
        assert len(logs) == 1
    finally:
        _cleanup()
```

- [ ] **Step 2: 运行确认失败**

Run: `cd backend && python -m pytest tests/test_meeting_report_api.py -k "start_report_endpoint or end_log" -v`
Expected: FAIL（404 / 无日志）。

- [ ] **Step 3: 实现端点与日志**

编辑 `backend/api/v1/meeting_records.py`：

(a) 顶部 import 区追加：
```python
from backend.services.operation_log_service import OperationLogService
```

(b) 在 `send_meeting_record` 之后（文件末尾）新增 start-report 端点：
```python
@router.post("/meeting-records/{session}/start-report", response_model=MeetingRecordResponse)
def start_meeting_report(
    session: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    """记录周会汇报开始时刻（管理员）。幂等：已开始则不覆盖。"""
    MeetingRecordService.start_report(db, session)
    OperationLogService.log(
        db, user=current_admin, action="meeting_report_start",
        description=f"开始第 {session} 次周会汇报",
    )
    return MeetingRecordService.get_session_detail(db, session)
```

(c) 修改现有 `close_meeting` 端点（行 68 起），在 close 前取 active session、close 后写日志：
```python
@router.post("/meeting-records/close", response_model=MeetingStateResponse)
def close_meeting(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    """关闭周会（管理员）：归档当前进行中的周会并关闭周会模式"""
    active = SettingsService.get_active_meeting_record(db)
    session = active.session if active else None
    MeetingRecordService.close_meeting(db)
    if session is not None:
        OperationLogService.log(
            db, user=current_admin, action="meeting_report_end",
            description=f"结束第 {session} 次周会",
        )
    return SettingsService.get_meeting_state(db)
```
（`SettingsService` 已在该文件 import；`MeetingRecordResponse` 已 import。）

- [ ] **Step 4: 运行确认通过**

Run: `cd backend && python -m pytest tests/test_meeting_report_api.py -v`
Expected: 全 PASS。

- [ ] **Step 5: 全后端回归**

Run: `cd backend && python -m pytest -q`
Expected: 全 PASS（含既有 test_meeting_record / test_settings_api 不破坏）。

- [ ] **Step 6: 提交**

```bash
git add backend/api/v1/meeting_records.py backend/tests/test_meeting_report_api.py
git commit -m "feat(backend): start-report 端点 + 开关会议操作日志"
```

---

## 阶段 D：前端类型与 API 客户端

### Task 8: types + resources API 客户端

**Files:**
- Modify: `frontend/src/types.ts`
- Modify: `frontend/src/api/resources.ts`

- [ ] **Step 1: 加类型**

在 `frontend/src/types.ts` 末尾追加：
```typescript
// 周会汇报页：汇报顺序与计时设置
export interface MeetingReportOrder {
  departments: string[]
  members: Record<string, string[]>
}

export interface MeetingTimerSettings {
  total_minutes: number
  person_threshold_minutes: number
}
```

- [ ] **Step 2: 加 API 方法**

编辑 `frontend/src/api/resources.ts`：

(a) 第 2 行的 `import type {...}` 追加 `MeetingReportOrder, MeetingTimerSettings`。

(b) 在 `settingsApi` 对象内（`importBackup` 之后、对象闭合 `}` 之前）追加：
```typescript
  getMeetingReportOrder() {
    return api.get<MeetingReportOrder>('/settings/meeting-report-order').then((r) => r.data)
  },
  setMeetingReportOrder(order: MeetingReportOrder) {
    return api.put<MeetingReportOrder>('/settings/meeting-report-order', order).then((r) => r.data)
  },
  getMeetingTimer() {
    return api.get<MeetingTimerSettings>('/settings/meeting-timer').then((r) => r.data)
  },
  setMeetingTimer(payload: MeetingTimerSettings) {
    return api.put<MeetingTimerSettings>('/settings/meeting-timer', payload).then((r) => r.data)
  },
```

(c) 在 `meetingApi` 对象内（`send` 之后）追加：
```typescript
  startReport(session: number) {
    return api.post<MeetingRecordDetail>(`/meeting-records/${session}/start-report`).then((r) => r.data)
  },
```

- [ ] **Step 3: 类型检查**

Run: `cd frontend && npx vue-tsc --noEmit`
Expected: 无错误（与本任务相关）。

- [ ] **Step 4: 提交**

```bash
git add frontend/src/types.ts frontend/src/api/resources.ts
git commit -m "feat(frontend): 汇报顺序/计时/开始汇报 的类型与 API 客户端"
```

---

## 阶段 E：抽屉重构（壳 + 内容组件）⚠️ 最高回归风险

> 目标：把 `ProjectDetailDrawer.vue`（1232 行）拆成「薄壳 `ProjectDetailDrawer.vue`」+「内容 `ProjectDetailContent.vue`」。
> 对外契约（5 props + 2 emit）保持不变；总览/看板用法零改动。
> 关闭拦截（未来时间校验 + 提交进展）通过 content 的 `defineExpose({ flushBeforeClose })` 暴露给壳调用。
> 因前端无单测，验证靠 `vue-tsc` + 手工。

### Task 9: 创建 ProjectDetailContent.vue（内容主体）

**Files:**
- Create: `frontend/src/components/ProjectDetailContent.vue`
- Reference: `frontend/src/components/ProjectDetailDrawer.vue`（拷贝来源）

- [ ] **Step 1: 复制原组件为 content 组件**

把 `frontend/src/components/ProjectDetailDrawer.vue` 整个文件内容复制到新文件 `frontend/src/components/ProjectDetailContent.vue`。后续步骤在 content 上做"去壳"改造。

- [ ] **Step 2: 去掉 el-drawer 外壳，模板根改为内容主体**

在 `ProjectDetailContent.vue` 中：删除最外层 `<el-drawer ... >`（原 L2–7）开标签与其对应闭合 `</el-drawer>`（原 L313 附近）。把 `<template>` 直接包裹原 `.detail` 根 div（原 L8–258）+ 两个 `el-dialog`（原 L261–312）。用一个根元素包裹（因为有 .detail 与两个 dialog 并列）：
```html
<template>
  <div class="detail-content-root">
    <!-- 原 .detail 根 div（v-if="local"） … 原样保留 -->
    <!-- 原 批注 el-dialog … 原样保留 -->
    <!-- 原 附件 el-dialog … 原样保留 -->
  </div>
</template>
```

- [ ] **Step 3: 调整 props / emits**

把 `defineProps`（原 L329–335）改为接收 `visible` 仍保留（内部 watch 依赖），其余不变：
```typescript
const props = withDefaults(defineProps<{
  visible: boolean
  project: Project | null
  departments?: string[]
  owners?: string[]
  createMode?: boolean
}>(), {
  departments: () => [],
  owners: () => [],
  createMode: false,
})
```
把 `defineEmits`（原 L337–340）改为：
```typescript
const emit = defineEmits<{
  (e: 'updated'): void
  (e: 'request-close'): void
}>()
```
说明：content 不再直接 emit `update:visible`；改为在需要关闭时 emit `request-close`，由壳决定关闭。

- [ ] **Step 4: 把 onVisible 关闭逻辑改造为 flushBeforeClose 并 expose**

原 `onVisible`（原 L897–907）是 drawer 的 `@update:model-value` 处理器：关闭时做未来时间校验 + `commitProgress` + emit。在 content 中替换为一个可被壳调用的方法，并用 `defineExpose` 暴露：
```typescript
/* 供壳在关闭前调用：执行未来时间校验 + 提交进展。
   返回 true=允许关闭，false=有未来时间，阻止关闭。 */
function flushBeforeClose(): boolean {
  const future = findFutureProgress()
  if (future) {
    ElMessage.warning('存在晚于当前时间的进展记录，请修正后再关闭')
    return false
  }
  commitProgress()
  return true
}

defineExpose({ flushBeforeClose })
```
删除原 `onVisible` 函数定义。`findFutureProgress`、`commitProgress` 保持在 content 内（它们本就在内容逻辑里）。

- [ ] **Step 5: 其余脚本逻辑原样保留**

第 1.5 节列出的所有 ref/computed/函数（local/editing/saving/form/sync/进展/批注/附件/历史/SVG 连线/生命周期 onMounted/onBeforeUnmount 等）**全部留在 content 内不动**。其中：
- `emit('updated')` 调用处（如 saveFields/saveCreate/removeProject/saveAnnotation/saveAttachment 内）保持不变。
- 任何原先 `emit('update:visible', false)` 的调用处，改为 `emit('request-close')`。
- `watch(() => props.visible, …)`（原 L430、L741）保留。

- [ ] **Step 6: 类型检查**

Run: `cd frontend && npx vue-tsc --noEmit`
Expected: `ProjectDetailContent.vue` 无类型错误（此时壳尚未改，可能有壳侧告警，下一个 Task 修）。

- [ ] **Step 7: 提交**

```bash
git add frontend/src/components/ProjectDetailContent.vue
git commit -m "refactor(frontend): 抽出 ProjectDetailContent（内容主体 + flushBeforeClose）"
```

---

### Task 10: ProjectDetailDrawer.vue 改为薄壳

**Files:**
- Modify (overwrite): `frontend/src/components/ProjectDetailDrawer.vue`

- [ ] **Step 1: 用薄壳整体替换 ProjectDetailDrawer.vue**

把 `frontend/src/components/ProjectDetailDrawer.vue` 全文替换为：
```vue
<template>
  <el-drawer
    :model-value="visible"
    size="62%"
    :with-header="false"
    @update:model-value="onDrawerToggle"
  >
    <ProjectDetailContent
      ref="contentRef"
      :visible="visible"
      :project="project"
      :departments="departments"
      :owners="owners"
      :create-mode="createMode"
      @updated="emit('updated')"
      @request-close="requestClose"
    />
  </el-drawer>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import ProjectDetailContent from './ProjectDetailContent.vue'
import type { Project } from '@/types'

/* 对外契约：与重构前完全一致的 5 props + 2 emit */
defineProps<{
  visible: boolean
  project: Project | null
  departments?: string[]
  owners?: string[]
  createMode?: boolean
}>()

const emit = defineEmits<{
  (e: 'update:visible', v: boolean): void
  (e: 'updated'): void
}>()

const contentRef = ref<InstanceType<typeof ProjectDetailContent> | null>(null)

/* el-drawer 自身触发的开关（点遮罩/ESC）：关闭时先让 content 做未来时间校验 + 提交进展 */
function onDrawerToggle(next: boolean) {
  if (!next) {
    requestClose()
  } else {
    emit('update:visible', true)
  }
}

/* content 主动请求关闭，或 drawer 关闭：统一走校验 */
function requestClose() {
  const ok = contentRef.value?.flushBeforeClose() ?? true
  if (ok) emit('update:visible', false)
}
</script>
```

- [ ] **Step 2: 类型检查**

Run: `cd frontend && npx vue-tsc --noEmit`
Expected: 无错误。

- [ ] **Step 3: 构建验证**

Run: `cd frontend && npx vite build`
Expected: 构建成功，无报错。

- [ ] **Step 4: 手工回归（关键）**

启动前端（`cd frontend && npm run dev`），在浏览器逐项验证抽屉在**项目总览页**与**看板页**行为不变：
- [ ] 打开抽屉、查看页头信息/完成度/字段网格正常
- [ ] 点"编辑"改字段并保存，列表刷新
- [ ] 进展详情：新增一条、编辑、删除、保存
- [ ] 批注（右键进展）与回复正常保存
- [ ] 文档附件添加/删除正常
- [ ] "历史修改记录" tab 正常加载
- [ ] 输入一个未来时间的进展 → 关闭抽屉时被拦截提示
- [ ] 关闭抽屉（点遮罩/ESC/按钮）均能正确关闭并提交进展
- [ ] 创建模式（总览页新建项目）正常

- [ ] **Step 5: 提交**

```bash
git add frontend/src/components/ProjectDetailDrawer.vue
git commit -m "refactor(frontend): ProjectDetailDrawer 改为薄壳，复用 ProjectDetailContent"
```

---

## 阶段 F：前端 store

### Task 11: meetingReport store（分组 + 顺序 + 计时）

**Files:**
- Create: `frontend/src/stores/meetingReport.ts`

- [ ] **Step 1: 新建 store**

新建 `frontend/src/stores/meetingReport.ts`：
```typescript
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { projectApi, departmentApi, settingsApi } from '@/api/resources'
import type { Project, Department, MeetingReportOrder } from '@/types'

/* 未分配兜底分组名（恒排在末尾） */
export const UNASSIGNED_DEPT = '未分配部门'
export const UNASSIGNED_OWNER = '未分配'

/* 仅汇报这三种状态：待启动/进行中/暂停 */
const REPORT_STATUSES = ['planned', 'in_progress', 'paused']

export interface MemberGroup { name: string; projects: Project[] }
export interface DeptGroup { dept: string; color?: string; members: MemberGroup[] }
/* 汇报序列里的一个"汇报位"=部门+个人 */
export interface PresenterSlot { dept: string; member: string }

export const useMeetingReportStore = defineStore('meetingReport', () => {
  const projects = ref<Project[]>([])
  const departments = ref<Department[]>([])
  const order = ref<MeetingReportOrder>({ departments: [], members: {} })
  const loading = ref(false)

  // 计时设置
  const totalMinutes = ref(30)
  const personThresholdMinutes = ref(5)

  // 当前选中
  const currentProjectId = ref<number | null>(null)

  // 计时运行时
  const running = ref(false)
  const totalRemaining = ref(0)        // 总剩余秒
  const personElapsed = ref(0)         // 当前汇报人已用秒
  let timer: ReturnType<typeof setInterval> | null = null

  /* 部门容错映射：按全称或简称匹配部门记录（与总览页一致） */
  function findDepartment(name?: string | null): Department | undefined {
    if (!name) return undefined
    const key = name.trim()
    return departments.value.find((d) => d.name === key || d.short_name === key)
  }

  /* 把项目按 部门→个人 分组，套用已存顺序，未排到的按兜底排末尾 */
  const grouped = computed<DeptGroup[]>(() => {
    // 1. 收集 部门 -> 个人 -> 项目
    const deptMap = new Map<string, Map<string, Project[]>>()
    for (const p of projects.value) {
      if (!REPORT_STATUSES.includes(p.status)) continue
      const dept = (p.department && p.department.trim()) || UNASSIGNED_DEPT
      const owner = (p.owner_name && p.owner_name.trim()) || UNASSIGNED_OWNER
      if (!deptMap.has(dept)) deptMap.set(dept, new Map())
      const m = deptMap.get(dept)!
      if (!m.has(owner)) m.set(owner, [])
      m.get(owner)!.push(p)
    }
    // 2. 部门排序：先按 order.departments，未列出的按名称，未分配置末尾
    const allDepts = Array.from(deptMap.keys())
    const sortedDepts = sortByOrder(allDepts, order.value.departments, UNASSIGNED_DEPT)
    // 3. 组装
    return sortedDepts.map((dept) => {
      const memberMap = deptMap.get(dept)!
      const allMembers = Array.from(memberMap.keys())
      const memberOrder = order.value.members[dept] || []
      const sortedMembers = sortByOrder(allMembers, memberOrder, UNASSIGNED_OWNER)
      return {
        dept,
        color: findDepartment(dept)?.color || undefined,
        members: sortedMembers.map((name) => ({ name, projects: memberMap.get(name)! })),
      }
    })
  })

  /* 通用：把 items 按 explicitOrder 排序，剩余按本地化名称，pinned 名称强制末尾 */
  function sortByOrder(items: string[], explicitOrder: string[], pinnedLast: string): string[] {
    const inOrder = explicitOrder.filter((x) => items.includes(x) && x !== pinnedLast)
    const rest = items
      .filter((x) => !inOrder.includes(x) && x !== pinnedLast)
      .sort((a, b) => a.localeCompare(b, 'zh'))
    const tail = items.includes(pinnedLast) ? [pinnedLast] : []
    return [...inOrder, ...rest, ...tail]
  }

  /* 扁平汇报序列：用于上一位/下一位翻页 */
  const presenters = computed<PresenterSlot[]>(() =>
    grouped.value.flatMap((d) => d.members.map((m) => ({ dept: d.dept, member: m.name }))),
  )

  /* 当前选中项目对象 */
  const currentProject = computed<Project | null>(() =>
    projects.value.find((p) => p.id === currentProjectId.value) || null,
  )

  /* 当前汇报位索引（由当前项目反推所属 部门+个人） */
  const currentPresenterIndex = computed<number>(() => {
    const p = currentProject.value
    if (!p) return -1
    const dept = (p.department && p.department.trim()) || UNASSIGNED_DEPT
    const member = (p.owner_name && p.owner_name.trim()) || UNASSIGNED_OWNER
    return presenters.value.findIndex((s) => s.dept === dept && s.member === member)
  })

  /* 加载数据：项目 + 部门 + 顺序 + 计时设置 */
  async function load() {
    loading.value = true
    try {
      const [ps, ds, ord, timer] = await Promise.all([
        projectApi.list({ limit: 1000 }),
        departmentApi.list(),
        settingsApi.getMeetingReportOrder(),
        settingsApi.getMeetingTimer(),
      ])
      projects.value = ps
      departments.value = ds
      order.value = ord
      totalMinutes.value = timer.total_minutes
      personThresholdMinutes.value = timer.person_threshold_minutes
      totalRemaining.value = totalMinutes.value * 60
      // 默认选中第一个汇报位的第一个项目
      const firstDept = grouped.value[0]
      const firstProj = firstDept?.members[0]?.projects[0]
      currentProjectId.value = firstProj?.id ?? null
    } finally {
      loading.value = false
    }
  }

  /* 选中某项目 */
  function selectProject(id: number) {
    if (id === currentProjectId.value) return
    // 切换汇报人时重置单人计时（仅当所属汇报位变化）
    const prevIdx = currentPresenterIndex.value
    currentProjectId.value = id
    if (currentPresenterIndex.value !== prevIdx) personElapsed.value = 0
  }

  /* 上一位 / 下一位：跳到相邻汇报位的第一个项目 */
  function gotoPresenter(delta: number) {
    const idx = currentPresenterIndex.value
    const next = idx + delta
    if (next < 0 || next >= presenters.value.length) return
    const slot = presenters.value[next]
    const dept = grouped.value.find((d) => d.dept === slot.dept)
    const member = dept?.members.find((m) => m.name === slot.member)
    const proj = member?.projects[0]
    if (proj) {
      currentProjectId.value = proj.id
      personElapsed.value = 0
    }
  }
  const nextPresenter = () => gotoPresenter(1)
  const prevPresenter = () => gotoPresenter(-1)

  /* 计时：每秒 tick */
  function start() {
    if (running.value) return
    running.value = true
    timer = setInterval(() => {
      if (totalRemaining.value > 0) totalRemaining.value -= 1
      personElapsed.value += 1
    }, 1000)
  }
  function stop() {
    running.value = false
    if (timer) { clearInterval(timer); timer = null }
  }
  function resetPerson() { personElapsed.value = 0 }

  /* 是否超时 */
  const personOvertime = computed(() => personElapsed.value >= personThresholdMinutes.value * 60)
  const totalOvertime = computed(() => totalRemaining.value <= 0)

  /* 拖拽后保存顺序 */
  async function saveOrder(next: MeetingReportOrder) {
    order.value = next
    await settingsApi.setMeetingReportOrder(next)
  }

  return {
    projects, departments, order, loading,
    totalMinutes, personThresholdMinutes,
    currentProjectId, currentProject, currentPresenterIndex,
    running, totalRemaining, personElapsed,
    grouped, presenters, personOvertime, totalOvertime,
    load, selectProject, nextPresenter, prevPresenter,
    start, stop, resetPerson, saveOrder, findDepartment,
  }
})
```

- [ ] **Step 2: 类型检查**

Run: `cd frontend && npx vue-tsc --noEmit`
Expected: 无错误。

- [ ] **Step 3: 提交**

```bash
git add frontend/src/stores/meetingReport.ts
git commit -m "feat(frontend): meetingReport store（分组/顺序/计时）"
```

---

## 阶段 G：前端组件与页面

### Task 12: MeetingReportTree（部门▸个人▸项目 拖拽树 + 查找）

**Files:**
- Create: `frontend/src/components/meeting-report/MeetingReportTree.vue`

- [ ] **Step 1: 新建组件**

新建 `frontend/src/components/meeting-report/MeetingReportTree.vue`。职责：渲染 `store.grouped` 三级树；部门级跨组拖拽、个人级组内拖拽（原生 HTML5 drag，参照 TaskBoardView 模式）；顶部查找框过滤；点击项目 `store.selectProject(id)`；高亮当前项目。

```vue
<template>
  <div class="mr-tree">
    <div class="mr-search">
      <el-input v-model="keyword" placeholder="🔍 查找项目 / 负责人 / 部门" clearable size="small" />
      <span class="mr-hint">⇅ 拖拽部门 / 组内拖拽个人 调整汇报顺序</span>
    </div>

    <div class="mr-scroll">
      <div
        v-for="(d, di) in filteredGroups"
        :key="d.dept"
        class="mr-dept"
        draggable="true"
        @dragstart="onDeptDragStart(di)"
        @dragover.prevent
        @drop="onDeptDrop(di)"
      >
        <div class="mr-dept-head">
          <span class="grip">⇅</span>
          <span class="swatch" :style="{ background: d.color || 'var(--c-ink-3)' }"></span>
          <b>{{ d.dept }}</b>
        </div>

        <div
          v-for="(m, mi) in d.members"
          :key="m.name"
          class="mr-member"
          draggable="true"
          @dragstart.stop="onMemberDragStart(d.dept, mi)"
          @dragover.prevent
          @drop.stop="onMemberDrop(d.dept, mi)"
        >
          <div class="mr-member-head">
            <span class="grip">⇅</span>{{ m.name }} ({{ m.projects.length }})
          </div>
          <div
            v-for="p in m.projects"
            :key="p.id"
            class="mr-proj"
            :class="{ cur: p.id === store.currentProjectId }"
            @click="store.selectProject(p.id)"
          >
            • {{ p.name }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { ElInput } from 'element-plus'
import { useMeetingReportStore } from '@/stores/meetingReport'
import type { MeetingReportOrder } from '@/types'

const store = useMeetingReportStore()
const keyword = ref('')

/* 关键词过滤：命中项目名/负责人/部门即保留该项目；保持分组结构 */
const filteredGroups = computed(() => {
  const kw = keyword.value.trim().toLowerCase()
  if (!kw) return store.grouped
  return store.grouped
    .map((d) => ({
      ...d,
      members: d.members
        .map((m) => ({
          ...m,
          projects: m.projects.filter((p) =>
            [p.name, p.owner_name, p.department].some((s) => (s || '').toLowerCase().includes(kw)),
          ),
        }))
        .filter((m) => m.projects.length > 0),
    }))
    .filter((d) => d.members.length > 0)
})

/* ---- 部门级拖拽：重排 order.departments ---- */
const dragDept = ref<number | null>(null)
function onDeptDragStart(i: number) { dragDept.value = i }
function onDeptDrop(target: number) {
  const from = dragDept.value
  dragDept.value = null
  if (from === null || from === target) return
  const depts = store.grouped.map((d) => d.dept)
  const moved = depts.splice(from, 1)[0]
  depts.splice(target, 0, moved)
  persist({ departments: depts, members: currentMembersOrder() })
}

/* ---- 个人级拖拽：仅组内重排 order.members[dept] ---- */
const dragMember = ref<{ dept: string; idx: number } | null>(null)
function onMemberDragStart(dept: string, idx: number) { dragMember.value = { dept, idx } }
function onMemberDrop(dept: string, target: number) {
  const d = dragMember.value
  dragMember.value = null
  if (!d || d.dept !== dept || d.idx === target) return  // 不允许跨部门
  const group = store.grouped.find((g) => g.dept === dept)!
  const names = group.members.map((m) => m.name)
  const moved = names.splice(d.idx, 1)[0]
  names.splice(target, 0, moved)
  const members = currentMembersOrder()
  members[dept] = names
  persist({ departments: store.grouped.map((g) => g.dept), members })
}

/* 当前各部门的个人顺序快照 */
function currentMembersOrder(): Record<string, string[]> {
  const m: Record<string, string[]> = {}
  for (const d of store.grouped) m[d.dept] = d.members.map((x) => x.name)
  return m
}

async function persist(order: MeetingReportOrder) {
  await store.saveOrder(order)
}
</script>

<style scoped>
.mr-tree { display: flex; flex-direction: column; height: 100%; }
.mr-search { padding: 8px; display: flex; flex-direction: column; gap: 4px; }
.mr-hint { font-size: 11px; color: var(--c-ink-3); }
.mr-scroll { flex: 1; overflow-y: auto; padding: 0 8px 8px; }
.mr-dept { margin-bottom: 6px; }
.mr-dept-head { display: flex; align-items: center; gap: 6px; padding: 4px 6px;
  background: var(--c-surface-2, #f2f3f5); border-radius: 6px; font-weight: 600; cursor: grab; }
.swatch { width: 10px; height: 10px; border-radius: 2px; }
.mr-member { margin: 4px 0 4px 14px; }
.mr-member-head { display: flex; align-items: center; gap: 4px; padding: 2px 6px;
  cursor: grab; color: var(--c-ink-2); }
.mr-proj { margin-left: 18px; padding: 3px 8px; border-radius: 5px; cursor: pointer;
  font-size: 13px; color: var(--c-ink-2); }
.mr-proj:hover { background: var(--c-surface-2, #f2f3f5); }
.mr-proj.cur { background: var(--c-accent, #3954d6); color: #fff; font-weight: 600; }
.grip { color: var(--c-ink-3); cursor: grab; }
</style>
```

- [ ] **Step 2: 类型检查**

Run: `cd frontend && npx vue-tsc --noEmit`
Expected: 无错误。

- [ ] **Step 3: 提交**

```bash
git add frontend/src/components/meeting-report/MeetingReportTree.vue
git commit -m "feat(frontend): 周会汇报树（部门/个人拖拽 + 查找）"
```

---

### Task 13: MeetingTopBar（梯形主席台 + 双计时 + 翻页 + 入口）

**Files:**
- Create: `frontend/src/components/meeting-report/MeetingTopBar.vue`

- [ ] **Step 1: 新建组件**

新建 `frontend/src/components/meeting-report/MeetingTopBar.vue`。职责：左侧会议信息 + 总时长倒计时；中部梯形主席台（上行汇报人 + 左右翻页箭头，下窄处本人计时）；右上"查看会议纪要 / 设置"。超时时对应区块加 `.overtime` 样式。计时格式 mm:ss。布局采用阶段确认的 A1 顶栏（梯形上大下小，clip-path）。

```vue
<template>
  <header class="mr-top">
    <!-- 左：会议信息 + 总时长 -->
    <div class="mr-left">
      <div class="mr-left-row">
        <b class="mr-title">周例会 · 第 {{ session }} 次</b>
        <span class="mr-total" :class="{ overtime: store.totalOvertime }">总 {{ fmt(store.totalRemaining) }}</span>
      </div>
      <span class="mr-date">{{ today }}</span>
    </div>

    <!-- 中：梯形主席台 -->
    <div class="mr-podium">
      <div class="mr-presenter">
        <button class="mr-arrow" :disabled="store.currentPresenterIndex <= 0" @click="store.prevPresenter()">‹</button>
        <div class="mr-name">
          <span class="mr-dept">{{ presenter?.dept || '—' }}</span>
          <span class="mr-nm">{{ presenter?.member || '—' }}</span>
        </div>
        <button class="mr-arrow" :disabled="store.currentPresenterIndex >= store.presenters.length - 1" @click="store.nextPresenter()">›</button>
      </div>
      <span class="mr-person" :class="{ overtime: store.personOvertime }">本人 {{ fmt(store.personElapsed) }}</span>
    </div>

    <!-- 右：纪要 + 设置 -->
    <div class="mr-actions">
      <el-button type="primary" @click="emit('view-minutes')">查看会议纪要</el-button>
      <el-button @click="emit('open-settings')">⚙ 设置</el-button>
    </div>
  </header>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { ElButton } from 'element-plus'
import { useMeetingReportStore } from '@/stores/meetingReport'

defineProps<{ session: number; today: string }>()
const emit = defineEmits<{ (e: 'view-minutes'): void; (e: 'open-settings'): void }>()

const store = useMeetingReportStore()
const presenter = computed(() => store.presenters[store.currentPresenterIndex] ?? null)

/* 秒 → mm:ss */
function fmt(total: number): string {
  const s = Math.max(0, Math.floor(total))
  const m = Math.floor(s / 60)
  const r = s % 60
  return `${String(m).padStart(2, '0')}:${String(r).padStart(2, '0')}`
}
</script>

<style scoped>
.mr-top { position: relative; display: flex; justify-content: space-between; align-items: flex-start;
  background: var(--c-surface, #fff); border-bottom: 2px solid var(--c-border, #e4e7ed);
  min-height: 64px; padding: 10px 16px; z-index: 5; }
.mr-left-row { display: flex; align-items: center; gap: 12px; }
.mr-title { font-size: 16px; }
.mr-date { color: var(--c-ink-3); font-size: 12px; }
.mr-total { font-size: 16px; font-weight: 800; font-variant-numeric: tabular-nums;
  color: #1a7f4b; background: #e3f5ea; padding: 2px 12px; border-radius: 6px; }
.mr-total.overtime, .mr-person.overtime { color: #fff; background: #d23b3b; animation: flash 1s steps(2) infinite; }
@keyframes flash { 50% { opacity: .45; } }
.mr-podium { position: absolute; left: 50%; transform: translateX(-50%); top: 6px;
  min-width: 320px; padding: 10px 22px 14px;
  background: linear-gradient(180deg, #eef1ff, #e3e8ff);
  border: 1px solid #c3ccf5; border-top: none;
  clip-path: polygon(0 0, 100% 0, 88% 100%, 12% 100%);
  box-shadow: 0 8px 18px rgba(0,0,0,.12);
  display: flex; flex-direction: column; align-items: center; gap: 8px; z-index: 6; }
.mr-presenter { display: flex; align-items: center; gap: 12px; }
.mr-arrow { width: 28px; height: 28px; border-radius: 50%; border: none; background: var(--c-accent, #3954d6);
  color: #fff; font-size: 16px; font-weight: 800; cursor: pointer; }
.mr-arrow:disabled { opacity: .35; cursor: not-allowed; }
.mr-name { display: flex; align-items: center; gap: 8px; }
.mr-dept { background: var(--c-accent, #3954d6); color: #fff; padding: 1px 8px; border-radius: 4px; font-size: 12px; }
.mr-nm { font-size: 18px; font-weight: 800; }
.mr-person { font-size: 15px; font-weight: 800; font-variant-numeric: tabular-nums;
  color: #8a5a00; background: #fff1d6; padding: 2px 14px; border-radius: 6px; }
.mr-actions { display: flex; gap: 8px; }
</style>
```

- [ ] **Step 2: 类型检查**

Run: `cd frontend && npx vue-tsc --noEmit`
Expected: 无错误。

- [ ] **Step 3: 提交**

```bash
git add frontend/src/components/meeting-report/MeetingTopBar.vue
git commit -m "feat(frontend): 周会顶栏梯形主席台（双计时 + 翻页 + 入口）"
```

---

### Task 14: MeetingReportView（页面外壳 + 设置弹窗 + 提示音）

**Files:**
- Create: `frontend/src/views/MeetingReportView.vue`

- [ ] **Step 1: 新建页面**

新建 `frontend/src/views/MeetingReportView.vue`。职责：全屏三段式（顶栏 + 左树 + 右详情）；挂载时 `store.load()` 并 `store.start()`、调用 `meetingApi.startReport(session)`；卸载时 `store.stop()`；右栏复用 `<ProjectDetailContent :visible="true" :project="store.currentProject" layout="meeting" />`（注意：需给 content 增加可选 `layout` prop 控制"页头固定+进展滚动"，见 Step 2）；设置弹窗改总时长/阈值并 `settingsApi.setMeetingTimer`；超时时 Web Audio 蜂鸣；"查看会议纪要"调用 `meetingApi.send(session)` 或打开现有纪要详情。

```vue
<template>
  <div class="mr-page">
    <MeetingTopBar :session="session" :today="today"
      @view-minutes="onViewMinutes" @open-settings="settingsVisible = true" />
    <div class="mr-body">
      <aside class="mr-aside"><MeetingReportTree /></aside>
      <main class="mr-main">
        <ProjectDetailContent v-if="store.currentProject" :visible="true"
          :project="store.currentProject" layout="meeting" @updated="store.load()" />
        <div v-else class="mr-empty">暂无待汇报项目</div>
      </main>
    </div>

    <el-dialog v-model="settingsVisible" title="计时设置" width="360px">
      <div class="mr-set-row">总会议时长（分钟）
        <el-input-number v-model="totalM" :min="1" :max="600" />
      </div>
      <div class="mr-set-row">单人提醒阈值（分钟）
        <el-input-number v-model="thresholdM" :min="1" :max="120" />
      </div>
      <template #footer>
        <el-button @click="settingsVisible = false">取消</el-button>
        <el-button type="primary" @click="saveSettings">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, onBeforeUnmount } from 'vue'
import { ElDialog, ElButton, ElInputNumber, ElMessage } from 'element-plus'
import MeetingTopBar from '@/components/meeting-report/MeetingTopBar.vue'
import MeetingReportTree from '@/components/meeting-report/MeetingReportTree.vue'
import ProjectDetailContent from '@/components/ProjectDetailContent.vue'
import { useMeetingReportStore } from '@/stores/meetingReport'
import { useMeetingStore } from '@/stores/meeting'
import { settingsApi, meetingApi } from '@/api/resources'

const store = useMeetingReportStore()
const meeting = useMeetingStore()

const session = ref(0)
const today = new Date().toISOString().slice(0, 10)
const settingsVisible = ref(false)
const totalM = ref(30)
const thresholdM = ref(5)

onMounted(async () => {
  await meeting.load()
  session.value = meeting.currentCount
  await store.load()
  totalM.value = store.totalMinutes
  thresholdM.value = store.personThresholdMinutes
  store.start()
  try { await meetingApi.startReport(session.value) } catch { /* 非阻断 */ }
})

onBeforeUnmount(() => store.stop())

/* 超时蜂鸣（Web Audio，无需音频文件） */
function beep() {
  try {
    const ctx = new (window.AudioContext || (window as any).webkitAudioContext)()
    const osc = ctx.createOscillator()
    osc.frequency.value = 880
    osc.connect(ctx.destination)
    osc.start(); osc.stop(ctx.currentTime + 0.2)
  } catch { /* ignore */ }
}
watch(() => store.personOvertime, (v, old) => { if (v && !old) beep() })
watch(() => store.totalOvertime, (v, old) => { if (v && !old) beep() })

async function saveSettings() {
  await settingsApi.setMeetingTimer({ total_minutes: totalM.value, person_threshold_minutes: thresholdM.value })
  store.totalMinutes = totalM.value
  store.personThresholdMinutes = thresholdM.value
  store.totalRemaining = totalM.value * 60
  settingsVisible.value = false
  ElMessage.success('已保存')
}

async function onViewMinutes() {
  try {
    const r = await meetingApi.send(session.value)
    ElMessage[r.ok ? 'success' : 'warning'](r.message)
  } catch {
    ElMessage.error('生成纪要失败')
  }
}
</script>

<style scoped>
.mr-page { position: fixed; inset: 0; display: flex; flex-direction: column;
  background: var(--c-canvas, #f5f6f8); z-index: 2000; }
.mr-body { flex: 1; display: flex; min-height: 0; }
.mr-aside { width: 24%; min-width: 240px; border-right: 1px solid var(--c-border, #e4e7ed);
  background: var(--c-surface, #fff); padding-top: 30px; }
.mr-main { flex: 1; overflow: hidden; padding-top: 30px; }
.mr-empty { display: grid; place-items: center; height: 100%; color: var(--c-ink-3); }
.mr-set-row { display: flex; justify-content: space-between; align-items: center; margin: 12px 0; }
</style>
```

- [ ] **Step 2: 给 ProjectDetailContent 增加 layout prop（页头固定+进展滚动）**

编辑 `frontend/src/components/ProjectDetailContent.vue`：
(a) `defineProps` 增加可选 `layout`：
```typescript
const props = withDefaults(defineProps<{
  visible: boolean
  project: Project | null
  departments?: string[]
  owners?: string[]
  createMode?: boolean
  layout?: 'drawer' | 'meeting'
}>(), {
  departments: () => [],
  owners: () => [],
  createMode: false,
  layout: 'drawer',
})
```
(b) 根元素绑定布局类：
```html
<div class="detail-content-root" :class="`layout-${props.layout}`">
```
(c) `<style scoped>` 末尾追加会议布局（页头固定、进展区滚动、占满高度）：
```css
.layout-meeting { height: 100%; display: flex; flex-direction: column; }
.layout-meeting .d-head,
.layout-meeting .brief-block,
.layout-meeting .prog-block,
.layout-meeting .d-fields { flex: none; }            /* 页头信息区固定 */
.layout-meeting .detail-tabs { flex: 1; min-height: 0; display: flex; flex-direction: column; }
.layout-meeting .detail-tabs :deep(.el-tabs__content) { flex: 1; overflow-y: auto; }  /* 进展区滚动 */
```
（若实际类名与上述不符，以 content 内真实模板类名为准微调；目标是"页头不滚、进展滚动"。）

- [ ] **Step 3: 类型检查 + 构建**

Run: `cd frontend && npx vue-tsc --noEmit && npx vite build`
Expected: 均成功。

- [ ] **Step 4: 提交**

```bash
git add frontend/src/views/MeetingReportView.vue frontend/src/components/ProjectDetailContent.vue
git commit -m "feat(frontend): 周会汇报页外壳 + 计时设置 + 超时蜂鸣 + 详情会议布局"
```

---

### Task 15: 路由接入 + 入口按钮

**Files:**
- Modify: `frontend/src/router/index.ts`
- Modify: `frontend/src/layouts/AppLayout.vue`（加入口；位置以现有周会横幅/导航为准）

- [ ] **Step 1: 加路由**

编辑 `frontend/src/router/index.ts`：在 `/`（AppLayout 容器）条目闭合 `},`（约 L40）之后、`]`（L41）之前，新增顶层非 public 路由：
```typescript
    {
      path: '/meeting-report',
      name: 'meeting-report',
      component: () => import('@/views/MeetingReportView.vue'),
    },
```

- [ ] **Step 2: 加入口按钮**

在 `frontend/src/layouts/AppLayout.vue` 顶部导航/周会横幅区，加一个跳转按钮（仅管理员可见，沿用现有 `auth`/`meeting` store 判断）：
```html
<el-button v-if="auth.isAdmin" type="primary" plain size="small"
  @click="$router.push('/meeting-report')">进入周会汇报</el-button>
```
（具体插入点与 `auth` 引用方式以 AppLayout 现有结构为准；若 AppLayout 未引入 `useAuthStore`，按现有 import 习惯补充。）

- [ ] **Step 3: 类型检查 + 构建**

Run: `cd frontend && npx vue-tsc --noEmit && npx vite build`
Expected: 均成功。

- [ ] **Step 4: 手工验证导航**

`npm run dev` → 以管理员登录 → 点"进入周会汇报" → 进入 `/meeting-report` 全屏页（无侧边栏）。

- [ ] **Step 5: 提交**

```bash
git add frontend/src/router/index.ts frontend/src/layouts/AppLayout.vue
git commit -m "feat(frontend): 接入 /meeting-report 路由与入口按钮"
```

---

## 阶段 H：视觉打磨与端到端验证

### Task 16: 用 Impeccable 打磨会议页视觉

**Files:**
- Modify: `frontend/src/views/MeetingReportView.vue`、`MeetingTopBar.vue`、`MeetingReportTree.vue` 及 `ProjectDetailContent.vue` 的会议布局样式

- [ ] **Step 1: 调用 Impeccable skill 做实景打磨**

按用户要求，UI 视觉用 Impeccable skill 在真实浏览器中迭代：梯形主席台质感、双计时醒目度与超时红闪、左树层级与拖拽反馈、右栏页头固定/进展滚动的视觉分隔、整体留白与对比度、深浅色适配（沿用项目 CSS 变量 `--c-*`）。以阶段 G 的 mockup（layout-v5）为视觉基准。

- [ ] **Step 2: 构建确认**

Run: `cd frontend && npx vue-tsc --noEmit && npx vite build`
Expected: 成功。

- [ ] **Step 3: 提交**

```bash
git add frontend/src/views/MeetingReportView.vue frontend/src/components/meeting-report/ frontend/src/components/ProjectDetailContent.vue
git commit -m "style(frontend): Impeccable 打磨周会汇报页视觉"
```

---

### Task 17: 端到端手工验证（验收）

**Files:** 无（验证任务）

- [ ] **Step 1: 后端全量测试**

Run: `cd backend && python -m pytest -q`
Expected: 全 PASS。

- [ ] **Step 2: 迁移在干净库上验证**

Run: `cd backend && python -m alembic upgrade head`
Expected: 升级到 `e1f2a3b4c5d6` 无错。

- [ ] **Step 3: 前端类型 + 构建**

Run: `cd frontend && npx vue-tsc --noEmit && npx vite build`
Expected: 均成功。

- [ ] **Step 4: 端到端走查（管理员登录，启动前后端）**

- [ ] 进入 `/meeting-report`，左树按"部门→个人→项目"分组，未分配排末尾。
- [ ] 拖拽部门顺序、组内拖拽个人 → 刷新页面后顺序保持（已存后端）。
- [ ] 顶栏梯形：汇报人显示正确，‹ › 翻页跳到相邻汇报位首个项目。
- [ ] 总计时倒计时、本人计时上数；切换汇报人时本人计时归零。
- [ ] 设置改总时长/阈值并保存；本人超阈值 → 梯形本人计时红闪+蜂鸣；总时长归零 → 总计时红闪+蜂鸣。
- [ ] 右栏详情：页头固定、进展区滚动；编辑字段/新增进展/批注/附件保存成功，列表刷新。
- [ ] "查看会议纪要"生成飞书文档（或按现有 send 行为反馈）。
- [ ] 关闭会议（现有关闭周会入口）后，`meeting_records` 该次 `ended_at` 有值、有 `meeting_report_start/end` 操作日志（可在"系统日志"页或 DB 核对）。
- [ ] 回归：项目总览/看板的抽屉编辑功能全部正常（重点）。

- [ ] **Step 5: 标记完成**

全部勾选后，本计划完成。等待用户统一提交（用户要求全部完成后再最终提交/汇总）。

---

## 自检记录（写计划后执行）

- **Spec 覆盖**：范围(3.1)→Task1-15；A1 布局(4)→Task12-14,16；前端架构(5)→Task8-15；数据分组(6)→Task11；顺序持久化(7)→Task3-5,11,12；计时(8)→Task5,11,13,14；后端改动(9)→Task1-7；生命周期权限(10)→Task7,14,15；测试策略(12)→各后端 Task 的 TDD + Task10/17 手工。✅ 全覆盖。
- **占位符扫描**：无 TBD/TODO；每个代码步骤含完整代码。✅
- **类型一致性**：`MeetingReportOrder{departments,members}`、`MeetingTimerSettings{total_minutes,person_threshold_minutes}` 前后端字段名一致；store `selectProject/nextPresenter/prevPresenter/start/stop/saveOrder` 与组件调用一致；`flushBeforeClose` 在 content 定义、壳调用一致。✅
- **已知风险**：阶段 E 抽屉重构无单测保护 → 用 Task10 Step4 手工回归清单 + Task17 Step4 兜底。
