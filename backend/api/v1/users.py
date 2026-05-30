"""用户管理 API

- 当前登录用户信息
- 用户列表（任意登录用户可见）
- 修改用户角色（仅管理员）
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from backend.api.deps import get_db
from backend.core.dependencies import get_current_user, get_current_admin
from backend.models.user import User, UserRole
from backend.schemas.user import UserResponse, UserRoleUpdate
from backend.services.user_service import UserService

router = APIRouter()


@router.get("/users/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """获取当前登录用户信息"""
    return current_user


@router.get("/users", response_model=List[UserResponse])
def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    role: Optional[UserRole] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取用户列表"""
    return UserService.get_list(db, skip=skip, limit=limit, role=role)


@router.patch("/users/{user_id}/role", response_model=UserResponse)
def update_user_role(
    user_id: int,
    payload: UserRoleUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    """修改用户角色（仅管理员）"""
    user = UserService.update_role(db, user_id, payload.role)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user
