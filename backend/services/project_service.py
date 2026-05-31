from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from backend.models.project import Project, ProjectStatus
from backend.schemas.project import ProjectCreate, ProjectUpdate

class ProjectService:
    """项目服务层"""

    @staticmethod
    def create(db: Session, project_data: ProjectCreate) -> Project:
        """创建项目"""
        project = Project(**project_data.model_dump())
        db.add(project)
        try:
            db.commit()
            db.refresh(project)
            return project
        except Exception:
            db.rollback()
            raise

    @staticmethod
    def get_by_id(db: Session, project_id: int) -> Optional[Project]:
        """根据ID获取项目"""
        return db.query(Project).filter(Project.id == project_id).first()

    @staticmethod
    def get_list(
        db: Session,
        skip: int = 0,
        limit: int = 20,
        status: Optional[ProjectStatus] = None,
        owner_name: Optional[str] = None,
        department: Optional[str] = None
    ) -> List[Project]:
        """获取项目列表（支持过滤）"""
        if skip < 0 or limit < 0:
            raise ValueError("skip and limit must be non-negative")

        query = db.query(Project)

        if status:
            query = query.filter(Project.status == status)
        if owner_name:
            query = query.filter(Project.owner_name == owner_name)
        if department:
            query = query.filter(Project.department == department)

        return query.offset(skip).limit(limit).all()

    @staticmethod
    def update(db: Session, project_id: int, project_data: ProjectUpdate) -> Optional[Project]:
        """更新项目"""
        project = ProjectService.get_by_id(db, project_id)
        if not project:
            return None

        update_data = project_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(project, field, value)

        try:
            db.commit()
            db.refresh(project)
            return project
        except Exception:
            db.rollback()
            raise

    @staticmethod
    def delete(db: Session, project_id: int) -> bool:
        """删除项目"""
        project = ProjectService.get_by_id(db, project_id)
        if not project:
            return False

        db.delete(project)
        try:
            db.commit()
            return True
        except Exception:
            db.rollback()
            raise
