from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from backend.models.base import BaseModel


class OperationLog(BaseModel):
    """系统操作日志（扁平操作流）

    记录用户的登录与项目操作（新增/更新进展/评论/反馈/删除/编辑），
    供管理员在「系统设置 › 系统日志」按时间范围查询。
    user_name 为冗余快照（用户改名/删除后日志仍可读）；
    description 为预渲染的操作描述（不含人名，人名前端单独蓝色显示）。
    仅向前记录——本功能上线前的历史操作无法补录。
    """
    __tablename__ = "operation_logs"

    user_id = Column(Integer, index=True, comment="操作人用户ID（可空）")
    project_id = Column(Integer, index=True, comment="关联项目ID（用于按项目查询历史；不级联删除，项目删除后日志保留）")
    user_name = Column(String(100), nullable=False, default="", comment="操作人姓名快照")
    action = Column(String(30), nullable=False, comment="动作类型 login/create_project/update_progress/comment/feedback/delete_project/edit_project")
    target = Column(String(200), comment="操作对象（如项目名）")
    description = Column(Text, nullable=False, default="", comment="预渲染操作描述（不含人名）")
    occurred_at = Column(DateTime, default=func.now(), nullable=False, index=True, comment="发生时间")

    def __repr__(self) -> str:
        return f"<OperationLog(user={self.user_name}, action={self.action}, at={self.occurred_at})>"
