from sqlalchemy.orm import Session
from typing import Dict, Any
import logging
from backend.core.security import create_access_token, create_refresh_token, verify_token
from backend.core.feishu import feishu_client
from backend.core.config import get_settings
from backend.models.user import UserRole
from backend.services.user_service import UserService
from backend.schemas.user import UserCreate

logger = logging.getLogger(__name__)


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
            # 身份标识优先用 open_id（自建应用恒定返回），回退 user_id / union_id。
            # user_id 仅在应用具备「获取用户 userID」权限时才有值。
            feishu_user_id = (
                user_info.get("open_id")
                or user_info.get("user_id")
                or user_info.get("union_id")
            )
            if not feishu_user_id:
                logger.error(
                    "No usable user identity from Feishu; returned keys=%s",
                    sorted(user_info.keys()),
                )
                raise AuthenticationError("Failed to get user ID from Feishu")
        except AuthenticationError:
            raise
        except Exception as e:
            raise AuthenticationError(f"Feishu API error: {str(e)}") from e

        # 3. 查找或创建用户
        # 初始管理员名单（飞书 open_id）：用于外网部署后让指定人员自动获得管理员权限
        initial_admin_ids = get_settings().INITIAL_ADMIN_FEISHU_IDS
        is_initial_admin = feishu_user_id in initial_admin_ids
        user = UserService.get_by_feishu_id(db, feishu_user_id)
        if not user:
            user_create = UserCreate(
                feishu_user_id=feishu_user_id,
                name=user_info.get("name", ""),
                name_en=user_info.get("en_name"),
                avatar_url=user_info.get("avatar_url"),
                department=user_info.get("department_name")
            )
            # 初始管理员首次登录即赋予管理员角色，其余为普通成员
            initial_role = UserRole.ADMIN if is_initial_admin else UserRole.MEMBER
            user = UserService.create(db, user_create, role=initial_role)
        else:
            user = UserService.update_last_login(db, user)
            # 每次登录确保：初始管理员若被降级或被导入覆盖，自动恢复为管理员
            user = UserService.ensure_initial_admin(db, user, initial_admin_ids)

        # 记录登录操作日志（失败不影响登录）
        from backend.services.operation_log_service import OperationLogService
        OperationLogService.log(db, user=user, action="login", description="登录了系统")

        # 4. 生成 JWT tokens（sub 必须为字符串，否则 JWT 校验会失败）
        access_token = create_access_token(data={"sub": str(user.id)})
        refresh_token = create_refresh_token(data={"sub": str(user.id)})

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

        # 刷新 token 时一并更新最后活跃时间：日常使用靠 token 静默续期维持会话，
        # 不会重新走飞书登录；若只在 OAuth 登录时更新，last_login_at 会严重滞后。
        # 在此更新使其反映最近活跃（最多滞后一个 access token 周期）。
        user = UserService.update_last_login(db, user)

        access_token = create_access_token(data={"sub": str(user.id)})

        return {
            "access_token": access_token,
            "token_type": "bearer"
        }
