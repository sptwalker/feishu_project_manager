from typing import List, Optional
from sqlalchemy.orm import Session
from backend.models.risk import Risk, RiskStatus
from backend.schemas.risk import RiskCreate, RiskUpdate

class RiskService:
    """风险服务层"""

    @staticmethod
    def create(db: Session, project_id: int, risk_data: RiskCreate) -> Risk:
        """创建风险"""
        risk = Risk(project_id=project_id, **risk_data.model_dump())
        db.add(risk)
        try:
            db.commit()
            db.refresh(risk)
            return risk
        except Exception:
            db.rollback()
            raise

    @staticmethod
    def get_by_id(db: Session, risk_id: int) -> Optional[Risk]:
        """根据ID获取风险"""
        return db.query(Risk).filter(Risk.id == risk_id).first()

    @staticmethod
    def get_list(
        db: Session,
        project_id: int,
        skip: int = 0,
        limit: int = 20,
        status: Optional[RiskStatus] = None,
        owner_id: Optional[int] = None,
    ) -> List[Risk]:
        """获取风险列表（支持过滤）"""
        if skip < 0 or limit < 0:
            raise ValueError("skip and limit must be non-negative")

        query = db.query(Risk).filter(Risk.project_id == project_id)

        if status:
            query = query.filter(Risk.status == status)
        if owner_id:
            query = query.filter(Risk.owner_id == owner_id)

        return query.offset(skip).limit(limit).all()

    @staticmethod
    def update(db: Session, risk_id: int, risk_data: RiskUpdate) -> Optional[Risk]:
        """更新风险"""
        risk = RiskService.get_by_id(db, risk_id)
        if not risk:
            return None

        update_data = risk_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(risk, field, value)

        try:
            db.commit()
            db.refresh(risk)
            return risk
        except Exception:
            db.rollback()
            raise

    @staticmethod
    def delete(db: Session, risk_id: int) -> bool:
        """删除风险"""
        risk = RiskService.get_by_id(db, risk_id)
        if not risk:
            return False

        db.delete(risk)
        try:
            db.commit()
            return True
        except Exception:
            db.rollback()
            raise
