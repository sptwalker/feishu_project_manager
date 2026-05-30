# 数据库模型与迁移系统 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建立完整的数据库模型系统，包括用户、项目、任务、事件溯源等核心表结构，并配置 Alembic 数据库迁移。

**Architecture:** 使用 SQLAlchemy 2.0 ORM 定义数据模型，Alembic 管理数据库迁移，支持 SQLite（开发）和 PostgreSQL（生产）。采用事件溯源模式记录所有变更历史。

**Tech Stack:** SQLAlchemy 2.0+, Alembic 1.13+, Pydantic v2, SQLite/PostgreSQL

---

## File Structure Overview

```
backend/
├── db/
│   ├── __init__.py
│   ├── base.py              # 数据库基类和会话管理
│   └── session.py           # 数据库会话工厂
├── models/
│   ├── __init__.py
│   ├── base.py              # SQLAlchemy Base 和通用 Mixin
│   ├── user.py              # 用户模型
│   ├── project.py           # 项目模型
│   ├── task.py              # 任务模型
│   ├── event.py             # 事件溯源模型
│   ├── progress_log.py      # 进度记录模型
│   ├── meeting.py           # 会议记录模型
│   ├── document.py          # 文档模型
│   ├── risk.py              # 风险模型
│   └── associations.py      # 关联表
├── alembic/
│   ├── env.py               # Alembic 环境配置
│   ├── script.py.mako       # 迁移脚本模板
│   └── versions/            # 迁移版本文件
├── alembic.ini              # Alembic 配置文件
└── tests/
    └── test_models.py       # 模型测试
```

---

### Task 1: 配置数据库基础设施

**Files:**
- Create: `backend/db/base.py`
- Create: `backend/db/session.py`
- Modify: `backend/core/config.py`

- [ ] **Step 1: 更新配置文件添加数据库配置**

```python
# backend/core/config.py - 在 Settings 类中添加
    # 数据库配置
    DATABASE_URL: str = "sqlite:///./data/feishu_pm.db"
    DATABASE_ECHO: bool = False  # SQL 日志
    
    @property
    def async_database_url(self) -> str:
        """获取异步数据库 URL"""
        if self.DATABASE_URL.startswith("sqlite"):
            return self.DATABASE_URL.replace("sqlite://", "sqlite+aiosqlite://")
        elif self.DATABASE_URL.startswith("postgresql"):
            return self.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
        return self.DATABASE_URL
```

- [ ] **Step 2: 创建数据库基类 backend/db/base.py**

```python
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import DeclarativeBase
from typing import Any

class Base(DeclarativeBase):
    """SQLAlchemy 声明式基类"""
    pass

# 导出 Base 供其他模块使用
__all__ = ["Base"]
```

- [ ] **Step 3: 创建数据库会话管理 backend/db/session.py**

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from backend.core.config import get_settings
from backend.db.base import Base

settings = get_settings()

# 创建同步引擎
engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.DATABASE_ECHO,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}
)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db() -> Session:
    """获取数据库会话依赖"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db() -> None:
    """初始化数据库（创建所有表）"""
    Base.metadata.create_all(bind=engine)
```

- [ ] **Step 4: 提交数据库基础设施**

```bash
git add backend/db/ backend/core/config.py
git commit -m "feat(db): add database infrastructure

- Add database base class and session management
- Add async database URL support
- Add database initialization function"
```

---

### Task 2: 创建用户模型

**Files:**
- Create: `backend/models/base.py`
- Create: `backend/models/user.py`

- [ ] **Step 1: 创建模型基类 backend/models/base.py**

```python
from datetime import datetime
from sqlalchemy import Column, Integer, DateTime
from sqlalchemy.sql import func
from backend.db.base import Base

class TimestampMixin:
    """时间戳 Mixin"""
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

class BaseModel(Base, TimestampMixin):
    """基础模型类"""
    __abstract__ = True
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
```

- [ ] **Step 2: 创建用户模型 backend/models/user.py**

```python
from sqlalchemy import Column, Integer, String, DateTime, Enum as SQLEnum
from sqlalchemy.orm import relationship
import enum
from backend.models.base import BaseModel

class UserRole(str, enum.Enum):
    """用户角色枚举"""
    ADMIN = "admin"
    PROJECT_MANAGER = "project_manager"
    MEMBER = "member"
    OBSERVER = "observer"

class User(BaseModel):
    """用户模型"""
    __tablename__ = "users"
    
    feishu_user_id = Column(String(100), unique=True, nullable=False, index=True, comment="飞书用户ID")
    name = Column(String(100), nullable=False, comment="姓名")
    avatar_url = Column(String(500), comment="头像URL")
    department = Column(String(100), comment="部门")
    role = Column(SQLEnum(UserRole), default=UserRole.MEMBER, nullable=False, comment="角色")
    last_login_at = Column(DateTime, comment="最后登录时间")
    
    # 关系
    owned_projects = relationship("Project", back_populates="owner", foreign_keys="Project.owner_id")
    owned_tasks = relationship("Task", back_populates="owner", foreign_keys="Task.owner_id")
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, name={self.name}, role={self.role})>"
```

- [ ] **Step 3: 提交用户模型**

```bash
git add backend/models/
git commit -m "feat(models): add user model

- Add base model with timestamp mixin
- Add user model with role enum
- Add relationships for projects and tasks"
```

---

### Task 3: 创建项目和任务模型

**Files:**
- Create: `backend/models/project.py`
- Create: `backend/models/task.py`

- [ ] **Step 1: 创建项目模型 backend/models/project.py**

```python
from sqlalchemy import Column, Integer, String, Text, Date, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
import enum
from backend.models.base import BaseModel

class ProjectStatus(str, enum.Enum):
    """项目状态枚举"""
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class ProjectUrgency(str, enum.Enum):
    """紧急程度枚举"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"

class Project(BaseModel):
    """项目模型"""
    __tablename__ = "projects"
    
    name = Column(String(200), nullable=False, comment="项目名称")
    record_date = Column(Date, nullable=False, comment="记录日期")
    content = Column(Text, comment="内容描述")
    status = Column(SQLEnum(ProjectStatus), default=ProjectStatus.PLANNED, nullable=False, comment="当前状态")
    urgency = Column(SQLEnum(ProjectUrgency), default=ProjectUrgency.MEDIUM, nullable=False, comment="紧急程度")
    department = Column(String(100), comment="负责部门")
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, comment="负责人ID")
    completion = Column(Integer, default=0, comment="完成度(0-100)")
    estimated_end_date = Column(Date, comment="预计完成时间")
    actual_end_date = Column(Date, comment="实际完成时间")
    
    # 关系
    owner = relationship("User", back_populates="owned_projects", foreign_keys=[owner_id])
    tasks = relationship("Task", back_populates="project", cascade="all, delete-orphan")
    risks = relationship("Risk", back_populates="project", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<Project(id={self.id}, name={self.name}, status={self.status})>"
```

- [ ] **Step 2: 创建任务模型 backend/models/task.py**

```python
from sqlalchemy import Column, Integer, String, Text, Date, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
import enum
from backend.models.base import BaseModel

class TaskStatus(str, enum.Enum):
    """任务状态枚举"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"

class TaskPriority(str, enum.Enum):
    """任务优先级枚举"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class Task(BaseModel):
    """任务模型"""
    __tablename__ = "tasks"
    
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True, comment="所属项目")
    parent_task_id = Column(Integer, ForeignKey("tasks.id"), comment="父任务ID")
    name = Column(String(200), nullable=False, comment="任务名称")
    description = Column(Text, comment="描述")
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, comment="负责人ID")
    status = Column(SQLEnum(TaskStatus), default=TaskStatus.PENDING, nullable=False, comment="当前状态")
    priority = Column(SQLEnum(TaskPriority), default=TaskPriority.MEDIUM, nullable=False, comment="优先级")
    completion = Column(Integer, default=0, comment="完成度(0-100)")
    due_date = Column(Date, comment="截止日期")
    start_date = Column(Date, comment="开始时间")
    end_date = Column(Date, comment="完成时间")
    
    # 关系
    project = relationship("Project", back_populates="tasks")
    owner = relationship("User", back_populates="owned_tasks", foreign_keys=[owner_id])
    parent_task = relationship("Task", remote_side=[BaseModel.id], backref="subtasks")
    
    def __repr__(self) -> str:
        return f"<Task(id={self.id}, name={self.name}, status={self.status})>"
```

- [ ] **Step 3: 提交项目和任务模型**

```bash
git add backend/models/project.py backend/models/task.py
git commit -m "feat(models): add project and task models

- Add project model with status and urgency enums
- Add task model with priority and parent task support
- Add relationships between project, task, and user"
```

---

### Task 4: 创建事件溯源和其他辅助模型

**Files:**
- Create: `backend/models/event.py`
- Create: `backend/models/progress_log.py`
- Create: `backend/models/meeting.py`
- Create: `backend/models/document.py`
- Create: `backend/models/risk.py`

- [ ] **Step 1: 创建事件模型 backend/models/event.py**

```python
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum as SQLEnum, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from backend.models.base import BaseModel

class EventType(str, enum.Enum):
    STATUS_CHANGE = "status_change"
    ASSIGNEE_CHANGE = "assignee_change"
    PROGRESS_UPDATE = "progress_update"
    DATE_ADJUST = "date_adjust"
    RISK_EVENT = "risk_event"
    ASSOCIATION = "association"
    SYSTEM_EVENT = "system_event"

class EntityType(str, enum.Enum):
    PROJECT = "project"
    TASK = "task"
    MEETING = "meeting"

class Event(BaseModel):
    __tablename__ = "events"
    
    event_type = Column(SQLEnum(EventType), nullable=False)
    entity_type = Column(SQLEnum(EntityType), nullable=False, index=True)
    entity_id = Column(Integer, nullable=False, index=True)
    triggered_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    occurred_at = Column(DateTime, default=func.now(), nullable=False, index=True)
    change_details = Column(JSON)
    description = Column(Text)
    
    triggered_by_user = relationship("User", foreign_keys=[triggered_by])
```

- [ ] **Step 2: 创建风险模型 backend/models/risk.py**

```python
from sqlalchemy import Column, Integer, String, Text, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
import enum
from backend.models.base import BaseModel

class RiskStatus(str, enum.Enum):
    OPEN = "open"
    MONITORING = "monitoring"
    RESOLVED = "resolved"

class Risk(BaseModel):
    __tablename__ = "risks"
    
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    status = Column(SQLEnum(RiskStatus), default=RiskStatus.OPEN)
    owner_id = Column(Integer, ForeignKey("users.id"))
    
    project = relationship("Project", back_populates="risks")
```

- [ ] **Step 3: 提交模型**

```bash
git add backend/models/
git commit -m "feat(models): add event and risk models"
```

---

### Task 5: 配置 Alembic 数据库迁移

**Files:**
- Create: `backend/alembic.ini`
- Modify: `backend/models/__init__.py`

- [ ] **Step 1: 初始化 Alembic**

```bash
cd backend
alembic init alembic
```

- [ ] **Step 2: 更新 models/__init__.py**

```python
from backend.models.user import User
from backend.models.project import Project
from backend.models.task import Task
from backend.models.event import Event
from backend.models.risk import Risk

__all__ = ["User", "Project", "Task", "Event", "Risk"]
```

- [ ] **Step 3: 生成初始迁移**

```bash
alembic revision --autogenerate -m "Initial schema"
alembic upgrade head
```

- [ ] **Step 4: 提交**

```bash
git add backend/alembic* backend/models/__init__.py
git commit -m "feat(db): configure Alembic migrations"
```

---

### Task 6: 验证和完成

- [ ] **Step 1: 测试数据库**

```bash
cd backend
python -c "from backend.db.session import init_db; init_db(); print('OK')"
```

- [ ] **Step 2: 最终提交**

```bash
git add -A
git commit -m "chore: complete phase 2 - database models

Phase 2 完成:
- 数据库基础设施
- 核心模型（用户、项目、任务、事件、风险）
- Alembic 迁移配置

下一步: Phase 3 - 认证系统"
git push origin main
```

---

## Execution Handoff

Plan saved to `docs/superpowers/plans/2026-05-30-phase2-database-models.md`.

**1. Subagent-Driven (recommended)** - Fresh subagent per task, review between tasks

**2. Inline Execution** - Execute in this session with checkpoints

**Which approach?**
