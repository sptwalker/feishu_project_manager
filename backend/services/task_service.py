from typing import List, Optional
from sqlalchemy.orm import Session
from backend.models.task import Task, TaskStatus, TaskPriority
from backend.schemas.task import TaskCreate, TaskUpdate

class TaskService:
    """任务服务层"""

    @staticmethod
    def create(db: Session, project_id: int, task_data: TaskCreate) -> Task:
        """创建任务"""
        task = Task(project_id=project_id, **task_data.model_dump())
        db.add(task)
        try:
            db.commit()
            db.refresh(task)
            return task
        except Exception:
            db.rollback()
            raise

    @staticmethod
    def get_by_id(db: Session, task_id: int) -> Optional[Task]:
        """根据ID获取任务"""
        return db.query(Task).filter(Task.id == task_id).first()

    @staticmethod
    def get_list(
        db: Session,
        project_id: int,
        skip: int = 0,
        limit: int = 20,
        status: Optional[TaskStatus] = None,
        priority: Optional[TaskPriority] = None,
        owner_id: Optional[int] = None,
        parent_task_id: Optional[int] = None,
    ) -> List[Task]:
        """获取任务列表（支持过滤）"""
        if skip < 0 or limit < 0:
            raise ValueError("skip and limit must be non-negative")

        query = db.query(Task).filter(Task.project_id == project_id)

        if status:
            query = query.filter(Task.status == status)
        if priority:
            query = query.filter(Task.priority == priority)
        if owner_id:
            query = query.filter(Task.owner_id == owner_id)
        if parent_task_id is not None:
            query = query.filter(Task.parent_task_id == parent_task_id)

        return query.offset(skip).limit(limit).all()

    @staticmethod
    def get_subtasks(db: Session, parent_task_id: int) -> List[Task]:
        """获取指定任务的子任务"""
        return db.query(Task).filter(Task.parent_task_id == parent_task_id).all()

    @staticmethod
    def update(db: Session, task_id: int, task_data: TaskUpdate) -> Optional[Task]:
        """更新任务"""
        task = TaskService.get_by_id(db, task_id)
        if not task:
            return None

        update_data = task_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(task, field, value)

        try:
            db.commit()
            db.refresh(task)
            return task
        except Exception:
            db.rollback()
            raise

    @staticmethod
    def delete(db: Session, task_id: int) -> bool:
        """删除任务"""
        task = TaskService.get_by_id(db, task_id)
        if not task:
            return False

        db.delete(task)
        try:
            db.commit()
            return True
        except Exception:
            db.rollback()
            raise
