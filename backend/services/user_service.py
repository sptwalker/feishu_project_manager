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
