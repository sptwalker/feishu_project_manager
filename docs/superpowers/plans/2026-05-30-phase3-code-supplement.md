# Phase 3 补充代码

## Task 4: 飞书 API 客户端完整代码

**backend/core/feishu.py**

```python
import httpx
from typing import Optional, Dict, Any
from backend.core.config import get_settings

settings = get_settings()

class FeishuClient:
    """飞书 API 客户端"""
    
    BASE_URL = "https://open.feishu.cn/open-apis"
    
    def __init__(self):
        self.app_id = settings.FEISHU_APP_ID
        self.app_secret = settings.FEISHU_APP_SECRET
        self._access_token: Optional[str] = None
    
    async def get_app_access_token(self) -> str:
        """获取应用 access token"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.BASE_URL}/auth/v3/app_access_token/internal",
                json={
                    "app_id": self.app_id,
                    "app_secret": self.app_secret
                }
            )
            response.raise_for_status()
            data = response.json()
            if data.get("code") != 0:
                raise Exception(f"Failed to get app access token: {data.get('msg')}")
            return data["app_access_token"]
    
    async def get_user_access_token(self, code: str) -> Dict[str, Any]:
        """通过 authorization code 获取用户 access token"""
        app_token = await self.get_app_access_token()
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.BASE_URL}/authen/v1/access_token",
                headers={"Authorization": f"Bearer {app_token}"},
                json={"grant_type": "authorization_code", "code": code}
            )
            response.raise_for_status()
            data = response.json()
            if data.get("code") != 0:
                raise Exception(f"Failed to get user access token: {data.get('msg')}")
            return data["data"]
    
    async def get_user_info(self, user_access_token: str) -> Dict[str, Any]:
        """获取用户信息"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/authen/v1/user_info",
                headers={"Authorization": f"Bearer {user_access_token}"}
            )
            response.raise_for_status()
            data = response.json()
            if data.get("code") != 0:
                raise Exception(f"Failed to get user info: {data.get('msg')}")
            return data["data"]
    
    def get_oauth_url(self, state: Optional[str] = None) -> str:
        """生成飞书 OAuth 授权 URL"""
        redirect_uri = settings.FEISHU_REDIRECT_URI
        url = f"https://open.feishu.cn/open-apis/authen/v1/authorize?app_id={self.app_id}&redirect_uri={redirect_uri}"
        if state:
            url += f"&state={state}"
        return url

# 全局飞书客户端实例
feishu_client = FeishuClient()
```

---

## Task 5: 认证服务层完整代码

**backend/services/user_service.py**

```python
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
from models.user import User, UserRole
from schemas.user import UserCreate

class UserService:
    """用户服务"""
    
    @staticmethod
    def get_by_id(db: Session, user_id: int) -> Optional[User]:
        """根据 ID 获取用户"""
        return db.query(User).filter(User.id == user_id).first()
    
    @staticmethod
    def get_by_feishu_id(db: Session, feishu_user_id: str) -> Optional[User]:
        """根据飞书用户 ID 获取用户"""
        return db.query(User).filter(User.feishu_user_id == feishu_user_id).first()
    
    @staticmethod
    def create(db: Session, user_data: UserCreate) -> User:
        """创建用户"""
        user = User(
            feishu_user_id=user_data.feishu_user_id,
            name=user_data.name,
            avatar_url=user_data.avatar_url,
            department=user_data.department,
            role=UserRole.MEMBER,
            last_login_at=datetime.utcnow()
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    
    @staticmethod
    def update_last_login(db: Session, user: User) -> User:
        """更新最后登录时间"""
        user.last_login_at = datetime.utcnow()
        db.commit()
        db.refresh(user)
        return user
```

**backend/services/auth_service.py**

```python
from sqlalchemy.orm import Session
from typing import Dict, Any
from backend.core.security import create_access_token, create_refresh_token, verify_token
from backend.core.feishu import feishu_client
from backend.services.user_service import UserService
from backend.schemas.user import UserCreate

class AuthService:
    """认证服务"""
    
    @staticmethod
    async def feishu_login(db: Session, code: str) -> Dict[str, Any]:
        """飞书 OAuth 登录"""
        # 1. 通过 code 获取用户 access token
        token_data = await feishu_client.get_user_access_token(code)
        user_access_token = token_data["access_token"]
        
        # 2. 获取用户信息
        user_info = await feishu_client.get_user_info(user_access_token)
        feishu_user_id = user_info["user_id"]
        
        # 3. 查找或创建用户
        user = UserService.get_by_feishu_id(db, feishu_user_id)
        if not user:
            user_create = UserCreate(
                feishu_user_id=feishu_user_id,
                name=user_info.get("name", ""),
                avatar_url=user_info.get("avatar_url"),
                department=user_info.get("department_name")
            )
            user = UserService.create(db, user_create)
        else:
            user = UserService.update_last_login(db, user)
        
        # 4. 生成 JWT tokens
        access_token = create_access_token(data={"sub": user.id})
        refresh_token = create_refresh_token(data={"sub": user.id})
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user": user
        }
    
    @staticmethod
    def refresh_access_token(db: Session, refresh_token: str) -> Dict[str, Any]:
        """刷新 access token"""
        payload = verify_token(refresh_token, token_type="refresh")
        if not payload:
            raise ValueError("Invalid refresh token")
        
        user_id = payload.get("sub")
        if not user_id:
            raise ValueError("Invalid token payload")
        
        user = UserService.get_by_id(db, user_id)
        if not user:
            raise ValueError("User not found")
        
        access_token = create_access_token(data={"sub": user.id})
        
        return {
            "access_token": access_token,
            "token_type": "bearer"
        }
```

**backend/services/__init__.py**

```python
from backend.services.auth_service import AuthService
from backend.services.user_service import UserService

__all__ = ["AuthService", "UserService"]
```
