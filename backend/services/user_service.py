from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime, timezone
from backend.models.user import User, UserRole
from backend.schemas.user import UserCreate

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
            # HttpUrl 是 Pydantic 对象，需转为字符串才能写入数据库
            avatar_url=str(user_data.avatar_url) if user_data.avatar_url else None,
            department=user_data.department,
            role=UserRole.MEMBER,
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
