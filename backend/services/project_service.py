from typing import List, Optional
from datetime import date
from sqlalchemy.orm import Session
from backend.models.project import Project, ProjectStatus
from backend.schemas.project import ProjectCreate, ProjectUpdate


class ProjectVersionConflict(Exception):
    """乐观锁冲突：客户端持有的 version 与数据库当前值不一致（项目已被他人修改）"""


class ProjectService:
    """项目服务层"""

    @staticmethod
    def create(db: Session, project_data: ProjectCreate) -> Project:
        """创建项目（记录日期自动取创建当天）"""
        data = project_data.model_dump()
        if not data.get("record_date"):
            data["record_date"] = date.today()
        project = Project(**data)
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
        """更新项目（乐观锁：客户端带 version 时与当前值比对，不一致抛 ProjectVersionConflict；
        version 自身由 version_id_col 在 flush 时自动 +1，并发提交另有 SQL 级 CAS 兜底）"""
        project = ProjectService.get_by_id(db, project_id)
        if not project:
            return None

        update_data = project_data.model_dump(exclude_unset=True)
        # version 不是业务字段：弹出仅用于比对，禁止 setattr 直接覆盖
        client_version = update_data.pop("version", None)
        if client_version is not None and project.version != client_version:
            raise ProjectVersionConflict()

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
