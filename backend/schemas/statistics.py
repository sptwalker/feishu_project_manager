from pydantic import BaseModel
from typing import Dict, Optional


class ProjectStats(BaseModel):
    total: int
    by_status: Dict[str, int]
    avg_completion: float
    overdue: int


class TaskStats(BaseModel):
    total: int
    by_status: Dict[str, int]
    overdue: int


class RiskStats(BaseModel):
    total: int
    by_status: Dict[str, int]


class DashboardResponse(BaseModel):
    projects: ProjectStats
    tasks: TaskStats
    risks: RiskStats


class ProjectProgressResponse(BaseModel):
    project_id: int
    project_name: str
    status: Optional[str]
    completion: int
    task_total: int
    task_completed: int
    task_completion_rate: float
    task_by_status: Dict[str, int]


class ImportResultResponse(BaseModel):
    created: int
    errors: list
    error_count: int
