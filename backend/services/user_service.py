from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime, timezone
from backend.models.user import User, UserRole, UserStatus
from backend.schemas.user import UserCreate, UserUpdate

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
    def create(db: Session, user_data: UserCreate, role: UserRole = UserRole.MEMBER,
               status: UserStatus = UserStatus.ACTIVE) -> User:
        """创建用户（role/status 可由调用方指定；登录新用户传 status=PENDING 走审批）"""
        user = User(
            feishu_user_id=user_data.feishu_user_id,
            name=user_data.name,
            name_en=user_data.name_en,
            # HttpUrl 是 Pydantic 对象，需转为字符串才能写入数据库
            avatar_url=str(user_data.avatar_url) if user_data.avatar_url else None,
            department=user_data.department,
            role=role,
            status=status,
            last_login_at=datetime.now(timezone.utc)
        )
        db.add(user)
        try:
            db.commit()
            db.refresh(user)
        except Exception:
            db.rollback()
            raise
        return user

    @staticmethod
    def ensure_initial_admin(db: Session, user: User, initial_admin_ids: List[str]) -> User:
        """确保初始管理员角色：若用户属于初始管理员名单且当前不是 admin，则提升为 admin。
        用于外网部署后，指定人员（按飞书 open_id 识别）每次登录都能恢复管理员权限，避免被锁在系统外。"""
        if user.feishu_user_id in initial_admin_ids and user.role != UserRole.ADMIN:
            return UserService.update_role(db, user.id, UserRole.ADMIN)
        return user

    @staticmethod
    def update_last_login(db: Session, user: User) -> User:
        """更新最后登录时间"""
        user.last_login_at = datetime.now(timezone.utc)
        try:
            db.commit()
            db.refresh(user)
        except Exception:
            db.rollback()
            raise
        return user

    @staticmethod
    def get_list(
        db: Session,
        skip: int = 0,
        limit: int = 50,
        role: Optional[UserRole] = None,
    ) -> List[User]:
        """获取用户列表（支持按角色过滤）"""
        if skip < 0 or limit < 0:
            raise ValueError("skip and limit must be non-negative")

        query = db.query(User)
        if role:
            query = query.filter(User.role == role)
        return query.offset(skip).limit(limit).all()

    @staticmethod
    def update_role(db: Session, user_id: int, role: UserRole) -> Optional[User]:
        """更新用户角色"""
        user = UserService.get_by_id(db, user_id)
        if not user:
            return None
        user.role = role
        try:
            db.commit()
            db.refresh(user)
        except Exception:
            db.rollback()
            raise
        return user

    @staticmethod
    def set_status(db: Session, user_id: int, status: UserStatus) -> Optional[User]:
        """设置用户准入状态（管理员审批：通过/禁用）"""
        user = UserService.get_by_id(db, user_id)
        if not user:
            return None
        user.status = status
        try:
            db.commit()
            db.refresh(user)
        except Exception:
            db.rollback()
            raise
        return user

    @staticmethod
    def update(db: Session, user_id: int, data: UserUpdate) -> Optional[User]:
        """管理员编辑用户：仅更新传入的字段（name/name_en/position/department/role）"""
        user = UserService.get_by_id(db, user_id)
        if not user:
            return None
        update_data = data.model_dump(exclude_unset=True)
        # discuss_perms 前端传 list（schema 已过滤到白名单），落库为 CSV 字符串列
        if "discuss_perms" in update_data:
            perms = update_data["discuss_perms"] or []
            update_data["discuss_perms"] = ",".join(perms)
        for field, value in update_data.items():
            setattr(user, field, value)
        try:
            db.commit()
            db.refresh(user)
        except Exception:
            db.rollback()
            raise
        return user
