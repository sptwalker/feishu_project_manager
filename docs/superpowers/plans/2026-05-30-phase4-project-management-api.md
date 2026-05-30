# 项目管理 API Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现完整的项目管理 CRUD API，包括项目创建、查询、更新、删除，以及项目成员管理和权限控制。

**Architecture:** 基于 FastAPI 构建 RESTful API，使用 SQLAlchemy ORM 进行数据库操作，通过依赖注入实现权限控制，支持分页、过滤、排序等查询功能。

**Tech Stack:** FastAPI 0.110+, SQLAlchemy 2.0+, Pydantic v2, pytest

---

## File Structure Overview

```
backend/
├── schemas/
│   └── project.py              # 项目相关 Schema
├── services/
│   └── project_service.py      # 项目业务逻辑
├── api/v1/
│   └── projects.py             # 项目路由
├── tests/
│   ├── test_project_service.py # 服务层测试
│   └── test_project_api.py     # API 测试
└── main.py                     # 注册项目路由
```

---

### Task 1: 创建项目 Schema

**Files:**
- Create: `backend/schemas/project.py`
- Test: `backend/tests/test_project_schema.py`

- [ ] **Step 1: 编写 Schema 验证测试**

```python
# backend/tests/test_project_schema.py
import pytest
from datetime import date
from pydantic import ValidationError
from backend.schemas.project import ProjectCreate, ProjectUpdate, ProjectResponse
from backend.models.project import ProjectStatus, ProjectUrgency

def test_project_create_valid():
    """测试有效的项目创建数据"""
    data = {
        "name": "测试项目",
        "record_date": "2026-05-30",
        "content": "项目描述",
        "status": "planned",
        "urgency": "medium",
        "department": "技术部",
        "owner_id": 1,
        "completion": 0,
        "estimated_end_date": "2026-12-31"
    }
    project = ProjectCreate(**data)
    assert project.name == "测试项目"
    assert project.completion == 0

def test_project_create_invalid_completion():
    """测试无效的完成度"""
    data = {
        "name": "测试项目",
        "record_date": "2026-05-30",
        "owner_id": 1,
        "completion": 150
    }
    with pytest.raises(ValidationError):
        ProjectCreate(**data)
```

- [ ] **Step 2: 运行测试确认失败**

```bash
cd backend
pytest tests/test_project_schema.py -v
```

Expected: FAIL with "ModuleNotFoundError: No module named 'backend.schemas.project'"

- [ ] **Step 3: 实现项目 Schema**

```python
# backend/schemas/project.py
from pydantic import BaseModel, Field, field_validator
from datetime import date
from typing import Optional
from backend.models.project import ProjectStatus, ProjectUrgency

class ProjectBase(BaseModel):
    """项目基础 Schema"""
    name: str = Field(..., min_length=1, max_length=200, description="项目名称")
    record_date: date = Field(..., description="记录日期")
    content: Optional[str] = Field(None, description="内容描述")
    status: ProjectStatus = Field(default=ProjectStatus.PLANNED, description="当前状态")
    urgency: ProjectUrgency = Field(default=ProjectUrgency.MEDIUM, description="紧急程度")
    department: Optional[str] = Field(None, max_length=100, description="负责部门")
    owner_id: int = Field(..., gt=0, description="负责人ID")
    completion: int = Field(default=0, ge=0, le=100, description="完成度")
    estimated_end_date: Optional[date] = Field(None, description="预计完成时间")

class ProjectCreate(ProjectBase):
    """创建项目 Schema"""
    pass

class ProjectUpdate(BaseModel):
    """更新项目 Schema"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    content: Optional[str] = None
    status: Optional[ProjectStatus] = None
    urgency: Optional[ProjectUrgency] = None
    department: Optional[str] = Field(None, max_length=100)
    owner_id: Optional[int] = Field(None, gt=0)
    completion: Optional[int] = Field(None, ge=0, le=100)
    estimated_end_date: Optional[date] = None
    actual_end_date: Optional[date] = None

class ProjectResponse(ProjectBase):
    """项目响应 Schema"""
    id: int
    actual_end_date: Optional[date] = None
    created_at: date
    updated_at: date

    class Config:
        from_attributes = True
```

- [ ] **Step 4: 运行测试确认通过**

```bash
pytest tests/test_project_schema.py -v
```

Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add backend/schemas/project.py backend/tests/test_project_schema.py
git commit -m "feat(project): add project schemas with validation"
```

---

### Task 2: 实现项目服务层

**Files:**
- Create: `backend/services/project_service.py`
- Test: `backend/tests/test_project_service.py`

- [ ] **Step 1: 编写服务层测试**

```python
# backend/tests/test_project_service.py
import pytest
from datetime import date
from sqlalchemy.orm import Session
from backend.services.project_service import ProjectService
from backend.schemas.project import ProjectCreate, ProjectUpdate
from backend.models.project import Project, ProjectStatus
from backend.models.user import User, UserRole

@pytest.fixture
def db_session():
    """数据库会话 fixture"""
    # 使用测试数据库
    from backend.db.session import SessionLocal
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture
def test_user(db_session):
    """创建测试用户"""
    user = User(
        feishu_user_id="test_user_123",
        name="测试用户",
        role=UserRole.MEMBER
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

def test_create_project(db_session, test_user):
    """测试创建项目"""
    project_data = ProjectCreate(
        name="新项目",
        record_date=date.today(),
        content="项目描述",
        owner_id=test_user.id
    )
    project = ProjectService.create(db_session, project_data)
    assert project.id is not None
    assert project.name == "新项目"
    assert project.owner_id == test_user.id

def test_get_project_by_id(db_session, test_user):
    """测试根据ID获取项目"""
    project_data = ProjectCreate(
        name="测试项目",
        record_date=date.today(),
        owner_id=test_user.id
    )
    created = ProjectService.create(db_session, project_data)
    fetched = ProjectService.get_by_id(db_session, created.id)
    assert fetched is not None
    assert fetched.id == created.id
```

- [ ] **Step 2: 运行测试确认失败**

```bash
pytest tests/test_project_service.py -v
```

Expected: FAIL with "ModuleNotFoundError: No module named 'backend.services.project_service'"

- [ ] **Step 3: 实现项目服务层**

```python
# backend/services/project_service.py
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from backend.models.project import Project, ProjectStatus
from backend.schemas.project import ProjectCreate, ProjectUpdate

class ProjectService:
    """项目服务层"""
    
    @staticmethod
    def create(db: Session, project_data: ProjectCreate) -> Project:
        """创建项目"""
        project = Project(**project_data.model_dump())
        db.add(project)
        db.commit()
        db.refresh(project)
        return project
    
    @staticmethod
    def get_by_id(db: Session, project_id: int) -> Optional[Project]:
        """根据ID获取项目"""
        return db.query(Project).filter(Project.id == project_id).first()
    
    @staticmethod
    def get_list(
        db: Session,
        skip: int = 0,
        limit: int = 20,
        status: Optional[ProjectStatus] = None,
        owner_id: Optional[int] = None,
        department: Optional[str] = None
    ) -> List[Project]:
        """获取项目列表（支持过滤）"""
        query = db.query(Project)
        
        if status:
            query = query.filter(Project.status == status)
        if owner_id:
            query = query.filter(Project.owner_id == owner_id)
        if department:
            query = query.filter(Project.department == department)
        
        return query.offset(skip).limit(limit).all()
    
    @staticmethod
    def update(db: Session, project_id: int, project_data: ProjectUpdate) -> Optional[Project]:
        """更新项目"""
        project = ProjectService.get_by_id(db, project_id)
        if not project:
            return None
        
        update_data = project_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(project, field, value)
        
        db.commit()
        db.refresh(project)
        return project
    
    @staticmethod
    def delete(db: Session, project_id: int) -> bool:
        """删除项目"""
        project = ProjectService.get_by_id(db, project_id)
        if not project:
            return False
        
        db.delete(project)
        db.commit()
        return True
```

- [ ] **Step 4: 运行测试确认通过**

```bash
pytest tests/test_project_service.py -v
```

Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add backend/services/project_service.py backend/tests/test_project_service.py
git commit -m "feat(project): add project service layer with CRUD operations"
```

---

### Task 3: 实现项目 API 路由

**Files:**
- Create: `backend/api/v1/projects.py`
- Test: `backend/tests/test_project_api.py`

- [ ] **Step 1: 编写 API 测试**

```python
# backend/tests/test_project_api.py
import pytest
from fastapi.testclient import TestClient
from datetime import date
from backend.main import app
from backend.models.user import User, UserRole
from backend.db.session import SessionLocal

client = TestClient(app)

@pytest.fixture
def auth_headers():
    """获取认证 token"""
    # 创建测试用户并获取 token
    db = SessionLocal()
    user = User(
        feishu_user_id="test_api_user",
        name="API测试用户",
        role=UserRole.ADMIN
    )
    db.add(user)
    db.commit()
    
    # 生成 token（假设已实现认证）
    from backend.core.security import create_access_token
    token = create_access_token({"sub": str(user.id)})
    db.close()
    
    return {"Authorization": f"Bearer {token}"}

def test_create_project_api(auth_headers):
    """测试创建项目 API"""
    response = client.post(
        "/api/v1/projects/",
        json={
            "name": "API测试项目",
            "record_date": "2026-05-30",
            "content": "通过API创建",
            "owner_id": 1
        },
        headers=auth_headers
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "API测试项目"
    assert "id" in data

def test_get_project_list_api(auth_headers):
    """测试获取项目列表 API"""
    response = client.get("/api/v1/projects/", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
```

- [ ] **Step 2: 运行测试确认失败**

```bash
pytest tests/test_project_api.py -v
```

Expected: FAIL with "404 Not Found" (路由未注册)

- [ ] **Step 3: 实现项目 API 路由**

```python
# backend/api/v1/projects.py
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from backend.api.deps import get_db, get_current_user
from backend.models.user import User
from backend.models.project import ProjectStatus
from backend.schemas.project import ProjectCreate, ProjectUpdate, ProjectResponse
from backend.services.project_service import ProjectService

router = APIRouter()

@router.post("/", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(
    project_data: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """创建项目"""
    project = ProjectService.create(db, project_data)
    return project

@router.get("/", response_model=List[ProjectResponse])
def get_projects(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[ProjectStatus] = None,
    owner_id: Optional[int] = None,
    department: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取项目列表"""
    projects = ProjectService.get_list(
        db, skip=skip, limit=limit,
        status=status, owner_id=owner_id, department=department
    )
    return projects

@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取单个项目"""
    project = ProjectService.get_by_id(db, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    return project

@router.put("/{project_id}", response_model=ProjectResponse)
def update_project(
    project_id: int,
    project_data: ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新项目"""
    project = ProjectService.update(db, project_id, project_data)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    return project

@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """删除项目"""
    success = ProjectService.delete(db, project_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
```

- [ ] **Step 4: 在 main.py 中注册路由**

```python
# backend/main.py - 添加项目路由
from backend.api.v1 import projects

app.include_router(
    projects.router,
    prefix="/api/v1/projects",
    tags=["projects"]
)
```

- [ ] **Step 5: 运行测试确认通过**

```bash
pytest tests/test_project_api.py -v
```

Expected: PASS

- [ ] **Step 6: 提交**

```bash
git add backend/api/v1/projects.py backend/main.py backend/tests/test_project_api.py
git commit -m "feat(project): add project CRUD API endpoints"
```

---

### Task 4: 添加项目权限控制

**Files:**
- Modify: `backend/api/v1/projects.py`
- Create: `backend/core/permissions.py`
- Test: `backend/tests/test_project_permissions.py`

- [ ] **Step 1: 编写权限测试**

```python
# backend/tests/test_project_permissions.py
import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.models.user import User, UserRole
from backend.models.project import Project
from backend.db.session import SessionLocal

client = TestClient(app)

def test_member_cannot_delete_others_project():
    """测试普通成员不能删除他人项目"""
    db = SessionLocal()
    
    # 创建项目所有者
    owner = User(feishu_user_id="owner_123", name="所有者", role=UserRole.MEMBER)
    db.add(owner)
    db.commit()
    
    # 创建项目
    project = Project(name="测试项目", record_date="2026-05-30", owner_id=owner.id)
    db.add(project)
    db.commit()
    
    # 创建另一个用户
    other_user = User(feishu_user_id="other_456", name="其他用户", role=UserRole.MEMBER)
    db.add(other_user)
    db.commit()
    
    # 生成其他用户的 token
    from backend.core.security import create_access_token
    token = create_access_token({"sub": str(other_user.id)})
    
    # 尝试删除项目
    response = client.delete(
        f"/api/v1/projects/{project.id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 403
    db.close()

def test_admin_can_delete_any_project():
    """测试管理员可以删除任何项目"""
    db = SessionLocal()
    
    owner = User(feishu_user_id="owner_789", name="所有者", role=UserRole.MEMBER)
    db.add(owner)
    db.commit()
    
    project = Project(name="测试项目2", record_date="2026-05-30", owner_id=owner.id)
    db.add(project)
    db.commit()
    
    admin = User(feishu_user_id="admin_001", name="管理员", role=UserRole.ADMIN)
    db.add(admin)
    db.commit()
    
    from backend.core.security import create_access_token
    token = create_access_token({"sub": str(admin.id)})
    
    response = client.delete(
        f"/api/v1/projects/{project.id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 204
    db.close()
```

- [ ] **Step 2: 运行测试确认失败**

```bash
pytest tests/test_project_permissions.py -v
```

Expected: FAIL (权限检查未实现)

- [ ] **Step 3: 实现权限检查工具**

```python
# backend/core/permissions.py
from fastapi import HTTPException, status
from backend.models.user import User, UserRole
from backend.models.project import Project

class PermissionChecker:
    """权限检查器"""
    
    @staticmethod
    def can_modify_project(user: User, project: Project) -> bool:
        """检查用户是否可以修改项目"""
        # 管理员可以修改任何项目
        if user.role == UserRole.ADMIN:
            return True
        # 项目所有者可以修改自己的项目
        if project.owner_id == user.id:
            return True
        return False
    
    @staticmethod
    def can_delete_project(user: User, project: Project) -> bool:
        """检查用户是否可以删除项目"""
        # 管理员可以删除任何项目
        if user.role == UserRole.ADMIN:
            return True
        # 项目所有者可以删除自己的项目
        if project.owner_id == user.id:
            return True
        return False
    
    @staticmethod
    def require_project_permission(user: User, project: Project, action: str = "modify"):
        """要求项目权限，否则抛出异常"""
        if action == "delete":
            has_permission = PermissionChecker.can_delete_project(user, project)
        else:
            has_permission = PermissionChecker.can_modify_project(user, project)
        
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"You don't have permission to {action} this project"
            )
```

- [ ] **Step 4: 在 API 路由中应用权限检查**

```python
# backend/api/v1/projects.py - 修改 update_project 和 delete_project 函数

from backend.core.permissions import PermissionChecker

@router.put("/{project_id}", response_model=ProjectResponse)
def update_project(
    project_id: int,
    project_data: ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新项目"""
    project = ProjectService.get_by_id(db, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # 权限检查
    PermissionChecker.require_project_permission(current_user, project, "modify")
    
    project = ProjectService.update(db, project_id, project_data)
    return project

@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """删除项目"""
    project = ProjectService.get_by_id(db, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # 权限检查
    PermissionChecker.require_project_permission(current_user, project, "delete")
    
    ProjectService.delete(db, project_id)
```

- [ ] **Step 5: 运行测试确认通过**

```bash
pytest tests/test_project_permissions.py -v
```

Expected: PASS

- [ ] **Step 6: 提交**

```bash
git add backend/core/permissions.py backend/api/v1/projects.py backend/tests/test_project_permissions.py
git commit -m "feat(project): add permission control for project operations"
```

---

## 验证清单

- [ ] 所有测试通过 (`pytest backend/tests/ -v`)
- [ ] API 文档可访问 (`http://localhost:8000/docs`)
- [ ] 项目 CRUD 操作正常
- [ ] 权限控制生效（普通用户只能操作自己的项目）
- [ ] 管理员可以操作所有项目

## 下一阶段计划

Phase 5 将实现：
1. 任务管理 API（任务 CRUD、子任务、任务分配）
2. 风险管理 API（风险记录、风险评估、风险跟踪）
3. 事件管理 API（项目事件记录、事件查询）
4. 飞书通知集成（项目变更通知、任务提醒）

