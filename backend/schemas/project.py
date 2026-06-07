from pydantic import BaseModel, Field, ConfigDict
from datetime import date, datetime
from typing import Optional, List
from backend.models.project import ProjectStatus, ProjectUrgency


class AnnotationReply(BaseModel):
    """批注回复"""
    id: str = Field(..., description="回复唯一标识")
    author_name: str = Field(..., description="回复人姓名")
    content: str = Field(..., max_length=128, description="回复内容")
    created_at: str = Field(..., description="创建时间")


class Annotation(BaseModel):
    """进展记录批注"""
    id: str = Field(..., description="批注唯一标识")
    author_name: str = Field(..., description="批注人姓名")
    content: str = Field(..., max_length=256, description="批注内容")
    created_at: str = Field(..., description="创建时间")
    replies: Optional[List['AnnotationReply']] = Field(default=None, description="批注回复列表")


class DocumentAttachment(BaseModel):
    """飞书文档附件"""
    url: str = Field(..., description="文档链接")
    title: Optional[str] = Field(None, description="文档标题")
    added_at: str = Field(..., description="添加时间")


class ProgressEntry(BaseModel):
    """项目进展记录条目"""
    time: str = Field(..., description="更新时间")
    content: str = Field("", description="内容")
    status: str = Field("正常", description="状况")
    meeting_session: Optional[int] = Field(None, description="周会次数（该条属于第几次周例会记录）")
    id: Optional[str] = Field(None, description="条目唯一标识")
    reply_to: Optional[str] = Field(None, description="反馈事件指向的原事件 id")
    annotations: Optional[List[Annotation]] = Field(default=None, description="批注列表")
    attachments: Optional[List[DocumentAttachment]] = Field(default=None, description="文档附件列表")


class ProjectBase(BaseModel):
    """项目基础 Schema"""
    name: str = Field(..., min_length=1, max_length=200, description="项目名称")
    record_date: date = Field(..., description="记录日期")
    content: Optional[str] = Field(None, description="简要说明")
    status: ProjectStatus = Field(default=ProjectStatus.PLANNED, description="当前状态")
    urgency: ProjectUrgency = Field(default=ProjectUrgency.MEDIUM, description="紧急程度")
    department: Optional[str] = Field(None, max_length=100, description="负责部门")
    owner_name: Optional[str] = Field(None, max_length=100, description="负责人姓名")
    related_name: Optional[str] = Field(None, max_length=200, description="相关人")
    completion: int = Field(default=0, ge=0, le=100, description="完成度")
    is_long_term: bool = Field(default=False, description="长期项目（不显示完成度）")
    estimated_end_date: Optional[date] = Field(None, description="预计完成时间")
    progress_log: Optional[List[ProgressEntry]] = Field(default=None, description="项目进展记录")

class ProjectCreate(ProjectBase):
    """创建项目 Schema（记录日期由后端自动记录为创建当天）"""
    record_date: Optional[date] = Field(None, description="记录日期（留空自动取今天）")

class ProjectUpdate(BaseModel):
    """更新项目 Schema"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    content: Optional[str] = None
    status: Optional[ProjectStatus] = None
    urgency: Optional[ProjectUrgency] = None
    department: Optional[str] = Field(None, max_length=100)
    owner_name: Optional[str] = Field(None, max_length=100)
    related_name: Optional[str] = Field(None, max_length=200)
    completion: Optional[int] = Field(None, ge=0, le=100)
    is_long_term: Optional[bool] = None
    estimated_end_date: Optional[date] = None
    actual_end_date: Optional[date] = None
    progress_log: Optional[List[ProgressEntry]] = None
    # 乐观锁：客户端打开时持有的版本号；带上则与 DB 当前值比对，不一致返回 409。
    # 过渡期可选（不带则跳过应用层比对，兼容旧客户端），后续可收紧为必填。
    version: Optional[int] = Field(None, description="乐观锁版本号（打开项目时获取的 version）")

class ProjectResponse(ProjectBase):
    """项目响应 Schema"""
    id: int
    actual_end_date: Optional[date] = None
    version: int = Field(1, description="乐观锁版本号（更新时带回以做并发校验）")
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
