# 飞书 OAuth 登录与 JWT 认证系统 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现完整的飞书 OAuth 2.0 登录流程和 JWT 令牌认证系统，包括用户注册、登录、令牌刷新和权限验证。

**Architecture:** 使用飞书开放平台 OAuth 2.0 进行用户身份验证，生成 JWT access token 和 refresh token，通过 FastAPI 依赖注入实现路由级别的权限控制。

**Tech Stack:** FastAPI 0.110+, python-jose[cryptography], passlib, lark-oapi SDK, Pydantic v2

---

## File Structure Overview

```
backend/
├── core/
│   ├── security.py          # JWT token 生成和验证
│   ├── dependencies.py      # FastAPI 依赖注入（认证、权限）
│   └── feishu.py           # 飞书 API 客户端封装
├── schemas/
│   ├── __init__.py
│   ├── auth.py             # 认证相关 Schema
│   └── user.py             # 用户相关 Schema
├── services/
│   ├── __init__.py
│   ├── auth_service.py     # 认证业务逻辑
│   └── user_service.py     # 用户业务逻辑
├── api/
│   ├── __init__.py
│   ├── deps.py             # API 依赖（数据库会话等）
│   └── v1/
│       ├── __init__.py
│       ├── auth.py         # 认证路由
│       └── users.py        # 用户路由
├── main.py                 # 应用入口（注册路由）
└── tests/
    ├── test_auth.py        # 认证测试
    └── test_security.py    # 安全工具测试
```

---

### Task 1: 配置飞书应用和安全密钥

**Files:**
- Modify: `backend/core/config.py`
- Create: `backend/.env.example`

- [ ] **Step 1: 更新配置文件添加认证相关配置**

```python
# backend/core/config.py - 在 Settings 类中添加

    # JWT 配置
    SECRET_KEY: str = "your-secret-key-here-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # 飞书应用配置
    FEISHU_APP_ID: str = ""
    FEISHU_APP_SECRET: str = ""
    FEISHU_REDIRECT_URI: str = "http://localhost:8000/api/v1/auth/feishu/callback"
    
    # 前端配置
    FRONTEND_URL: str = "http://localhost:3000"
    
    class Config:
        env_file = ".env"
        case_sensitive = True
```

- [ ] **Step 2: 创建环境变量示例文件 backend/.env.example**

```bash
# 数据库配置
DATABASE_URL=sqlite:///./data/feishu_pm.db
DATABASE_ECHO=false

# JWT 配置
SECRET_KEY=your-secret-key-here-please-change-this-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# 飞书应用配置（需要在飞书开放平台创建应用）
FEISHU_APP_ID=your_app_id
FEISHU_APP_SECRET=your_app_secret
FEISHU_REDIRECT_URI=http://localhost:8000/api/v1/auth/feishu/callback

# 前端配置
FRONTEND_URL=http://localhost:3000
```

- [ ] **Step 3: 提交配置更改**

```bash
git add backend/core/config.py backend/.env.example
git commit -m "feat(auth): add authentication configuration

- Add JWT token configuration
- Add Feishu OAuth app configuration
- Add environment variable example file"
```

---

### Task 2: 实现 JWT 安全工具

**Files:**
- Create: `backend/core/security.py`

- [ ] **Step 1: 创建 JWT token 工具 backend/core/security.py**

```python
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from backend.core.config import get_settings

settings = get_settings()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """创建 JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: Dict[str, Any]) -> str:
    """创建 JWT refresh token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def verify_token(token: str, token_type: str = "access") -> Optional[Dict[str, Any]]:
    """验证 JWT token"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("type") != token_type:
            return None
        return payload
    except JWTError:
        return None

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """生成密码哈希"""
    return pwd_context.hash(password)
```

- [ ] **Step 2: 提交安全工具**

```bash
git add backend/core/security.py
git commit -m "feat(auth): add JWT token utilities

- Add access token and refresh token creation
- Add token verification
- Add password hashing utilities"
```

---

### Task 3: 创建认证相关 Schema

**Files:**
- Create: `backend/schemas/auth.py`
- Create: `backend/schemas/user.py`
- Modify: `backend/schemas/__init__.py`

- [ ] **Step 1: 创建认证 Schema backend/schemas/auth.py**

```python
from pydantic import BaseModel, Field
from typing import Optional

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class TokenPayload(BaseModel):
    sub: Optional[int] = None
    exp: Optional[int] = None
    type: Optional[str] = None

class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(..., description="Refresh token")

class FeishuCallbackParams(BaseModel):
    code: str = Field(..., description="Authorization code")
    state: Optional[str] = Field(None, description="State parameter")
```

- [ ] **Step 2: 创建用户 Schema backend/schemas/user.py**

```python
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from models.user import UserRole

class UserBase(BaseModel):
    name: str = Field(..., max_length=100)
    department: Optional[str] = Field(None, max_length=100)

class UserCreate(UserBase):
    feishu_user_id: str = Field(..., max_length=100)
    avatar_url: Optional[str] = Field(None, max_length=500)

class UserInDB(UserBase):
    id: int
    feishu_user_id: str
    avatar_url: Optional[str]
    role: UserRole
    last_login_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class UserResponse(UserInDB):
    pass
```

- [ ] **Step 3: 提交 Schema**

```bash
git add backend/schemas/
git commit -m "feat(schemas): add authentication and user schemas"
```

---

### Task 4: 实现飞书 API 客户端

**Files:**
- Create: `backend/core/feishu.py`

- [ ] **Step 1: 创建飞书客户端（见完整代码）**

- [ ] **Step 2: 提交飞书客户端**

```bash
git add backend/core/feishu.py
git commit -m "feat(feishu): add Feishu API client"
```

---

### Task 5: 实现认证服务层

**Files:**
- Create: `backend/services/auth_service.py`
- Create: `backend/services/user_service.py`

- [ ] **Step 1: 创建服务层文件（见完整代码）**

- [ ] **Step 2: 提交服务层**

```bash
git add backend/services/
git commit -m "feat(services): add authentication and user services"
```

---

### Task 6: 实现 FastAPI 依赖注入

**Files:**
- Create: `backend/core/dependencies.py`
- Create: `backend/api/deps.py`

- [ ] **Step 1: 创建认证依赖 backend/core/dependencies.py**

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional
from backend.core.security import verify_token
from backend.services.user_service import UserService
from backend.api.deps import get_db
from models.user import User, UserRole

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    token = credentials.credentials
    payload = verify_token(token, token_type="access")
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )
    
    user = UserService.get_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user

def require_role(required_role: UserRole):
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role != required_role and current_user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        return current_user
    return role_checker

async def get_current_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user
```

- [ ] **Step 2: 创建数据库依赖 backend/api/deps.py**

```python
from typing import Generator
from backend.db.session import SessionLocal

def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

- [ ] **Step 3: 提交依赖注入**

```bash
git add backend/core/dependencies.py backend/api/deps.py
git commit -m "feat(deps): add authentication dependencies

- Add get_current_user dependency
- Add role-based access control
- Add database session dependency"
```

---

### Task 7: 实现认证 API 路由

**Files:**
- Create: `backend/api/v1/auth.py`
- Create: `backend/api/v1/__init__.py`
- Modify: `backend/api/__init__.py`

- [ ] **Step 1: 创建认证路由 backend/api/v1/auth.py**

```python
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from backend.api.deps import get_db
from backend.services.auth_service import AuthService
from backend.schemas.auth import Token, RefreshTokenRequest, FeishuCallbackParams
from backend.core.feishu import feishu_client
from backend.core.config import get_settings

settings = get_settings()
router = APIRouter(prefix="/auth", tags=["authentication"])

@router.get("/feishu/login")
async def feishu_login():
    oauth_url = feishu_client.get_oauth_url()
    return RedirectResponse(url=oauth_url)

@router.get("/feishu/callback", response_model=Token)
async def feishu_callback(
    code: str,
    state: str = None,
    db: Session = Depends(get_db)
):
    try:
        result = await AuthService.feishu_login(db, code)
        return Token(
            access_token=result["access_token"],
            refresh_token=result["refresh_token"],
            token_type=result["token_type"]
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Login failed: {str(e)}"
        )

@router.post("/refresh", response_model=Token)
async def refresh_token(
    request: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    try:
        result = AuthService.refresh_access_token(db, request.refresh_token)
        return Token(
            access_token=result["access_token"],
            refresh_token=request.refresh_token,
            token_type=result["token_type"]
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )

@router.post("/logout")
async def logout():
    return {"message": "Logged out successfully"}
```

- [ ] **Step 2: 提交认证路由**

```bash
git add backend/api/v1/
git commit -m "feat(api): add authentication routes

- Add Feishu OAuth login endpoint
- Add OAuth callback handler
- Add token refresh endpoint
- Add logout endpoint"
```

---

### Task 8: 注册路由到主应用

**Files:**
- Modify: `backend/main.py`

- [ ] **Step 1: 更新 main.py 注册路由**

```python
# backend/main.py - 添加路由注册
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.core.config import get_settings
from backend.api.v1 import auth

settings = get_settings()

app = FastAPI(
    title="Feishu Project Manager API",
    description="飞书项目管理系统 API",
    version="1.0.0"
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(auth.router, prefix="/api/v1")

@app.get("/")
async def root():
    return {"message": "Feishu Project Manager API"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
```

- [ ] **Step 2: 提交主应用更新**

```bash
git add backend/main.py
git commit -m "feat(main): register authentication routes

- Add CORS middleware
- Register auth router
- Add health check endpoint"
```

---

### Task 9: 验证和完成

- [ ] **Step 1: 安装依赖**

```bash
cd backend
pip install python-jose[cryptography] passlib[bcrypt] httpx python-multipart
pip freeze > requirements.txt
```

- [ ] **Step 2: 测试认证流程**

```bash
# 启动服务器
python main.py

# 访问 http://localhost:8000/docs 查看 API 文档
# 测试 /api/v1/auth/feishu/login 端点
```

- [ ] **Step 3: 最终提交**

```bash
git add backend/requirements.txt
git commit -m "chore: complete phase 3 - authentication system

Phase 3 完成:
- 飞书 OAuth 2.0 登录
- JWT token 认证
- 用户管理服务
- 权限控制依赖

下一步: Phase 4 - 项目管理 API"
git push origin main
```

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-05-30-phase3-authentication-system.md`.

**1. Subagent-Driven (recommended)** - Fresh subagent per task, review between tasks

**2. Inline Execution** - Execute in this session with checkpoints

**Which approach?**
