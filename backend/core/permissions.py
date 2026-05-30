from typing import Literal
from fastapi import HTTPException, status
from backend.models.user import User, UserRole
from backend.models.project import Project
from backend.models.task import Task


class PermissionChecker:
    """权限检查器

    Permission Policy:
    - ADMIN: Can modify and delete any project
    - Project Owner (any role): Can modify and delete their own project
    - PROJECT_MANAGER, MEMBER, OBSERVER: Cannot modify or delete projects they don't own

    Note: PROJECT_MANAGER currently has no special privileges for project mutations.
    This may change as the product evolves.
    """

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
    def require_project_permission(
        user: User,
        project: Project,
        action: Literal["modify", "delete"] = "modify",
    ):
        """要求项目权限，否则抛出异常"""
        if action == "delete":
            has_permission = PermissionChecker.can_delete_project(user, project)
        elif action == "modify":
            has_permission = PermissionChecker.can_modify_project(user, project)
        else:
            raise ValueError(f"Unknown action: {action}")

        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"You don't have permission to {action} this project"
            )

    @staticmethod
    def can_mutate_task(user: User, task: Task, project: Project) -> bool:
        """检查用户是否可以修改/删除任务

        Task Permission Policy:
        - ADMIN: Can mutate any task
        - Task Owner: Can mutate their own task
        - Parent Project Owner: Can mutate tasks within their project
        """
        # 管理员可以操作任何任务
        if user.role == UserRole.ADMIN:
            return True
        # 任务负责人可以操作自己的任务
        if task.owner_id == user.id:
            return True
        # 所属项目的所有者可以操作项目内的任务
        if project is not None and project.owner_id == user.id:
            return True
        return False

    @staticmethod
    def require_task_permission(
        user: User,
        task: Task,
        project: Project,
        action: Literal["modify", "delete"] = "modify",
    ):
        """要求任务权限，否则抛出异常"""
        if action not in ("modify", "delete"):
            raise ValueError(f"Unknown action: {action}")

        if not PermissionChecker.can_mutate_task(user, task, project):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"You don't have permission to {action} this task"
            )
