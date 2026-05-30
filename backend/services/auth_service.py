from sqlalchemy.orm import Session
from typing import Dict, Any
from backend.core.security import create_access_token, create_refresh_token, verify_token
from backend.core.feishu import feishu_client
from backend.services.user_service import UserService
from backend.schemas.user import UserCreate


class AuthenticationError(Exception):
    """认证错误"""
    pass


class InvalidTokenError(AuthenticationError):
    """无效的令牌"""
    pass


class AuthService:
    """认证服务"""

    @staticmethod
    async def feishu_login(db: Session, code: str) -> Dict[str, Any]:
        """飞书 OAuth 登录"""
        # 验证输入
        if not code or not code.strip():
            raise AuthenticationError("Authorization code is required")

        try:
            # 1. 通过 code 获取用户 access token
            token_data = await feishu_client.get_user_access_token(code)
            user_access_token = token_data.get("access_token")
            if not user_access_token:
                raise AuthenticationError("Failed to get access token from Feishu")

            # 2. 获取用户信息
            user_info = await feishu_client.get_user_info(user_access_token)
            feishu_user_id = user_info.get("user_id")
            if not feishu_user_id:
                raise AuthenticationError("Failed to get user ID from Feishu")
        except AuthenticationError:
            raise
        except Exception as e:
            raise AuthenticationError(f"Feishu API error: {str(e)}") from e

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
            raise InvalidTokenError("Invalid refresh token")

        user_id = payload.get("sub")
        if not user_id:
            raise InvalidTokenError("Invalid token payload")

        user = UserService.get_by_id(db, user_id)
        if not user:
            raise InvalidTokenError("User not found")

        access_token = create_access_token(data={"sub": user.id})

        return {
            "access_token": access_token,
            "token_type": "bearer"
        }
