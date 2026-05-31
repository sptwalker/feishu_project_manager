from typing import Literal, Optional
from fastapi import HTTPException, status
from backend.models.user import User, UserRole
from backend.models.project import Project
from backend.models.task import Task
from backend.models.risk import Risk

# 可管理项目数据（增删改）的角色
MANAGER_ROLES = (UserRole.ADMIN, UserRole.PROJECT_MANAGER)


class PermissionChecker:
    """权限检查器（基于角色，与项目数据解耦）

    Permission Policy:
    - ADMIN / PROJECT_MANAGER: 可增删改任何项目 / 任务 / 风险
    - MEMBER / OBSERVER: 只读

    说明：项目数据不再绑定负责人用户账号，因此权限完全由角色决定；
    增删用户、调整用户角色都不会影响已有的项目数据。
    """

    @staticmethod
    def can_manage(user: User) -> bool:
        """是否具备管理（增删改）权限"""
        return user.role in MANAGER_ROLES

    @staticmethod
    def _require(user: User, action: str, entity: str):
        if action not in ("modify", "delete"):
            raise ValueError(f"Unknown action: {action}")
        if not PermissionChecker.can_manage(user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"You don't have permission to {action} this {entity}",
            )

    @staticmethod
    def require_project_permission(
        user: User,
        project: Optional[Project] = None,
        action: Literal["modify", "delete"] = "modify",
    ):
        """要求项目管理权限（project 参数保留以兼容调用方，实际按角色判定）"""
        PermissionChecker._require(user, action, "project")

    @staticmethod
    def require_task_permission(
        user: User,
        task: Optional[Task] = None,
        project: Optional[Project] = None,
        action: Literal["modify", "delete"] = "modify",
    ):
        """要求任务管理权限"""
        PermissionChecker._require(user, action, "task")

    @staticmethod
    def require_risk_permission(
        user: User,
        risk: Optional[Risk] = None,
        project: Optional[Project] = None,
        action: Literal["modify", "delete"] = "modify",
    ):
        """要求风险管理权限"""
        PermissionChecker._require(user, action, "risk")
