"""系统操作日志 API（仅管理员）

按时间范围查询用户操作记录（登录/项目操作）。
"""
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.api.deps import get_db
from backend.core.dependencies import get_current_admin
from backend.models.user import User
from backend.schemas.operation_log import OperationLogResponse
from backend.services.operation_log_service import OperationLogService

router = APIRouter()


@router.get("/operation-logs", response_model=List[OperationLogResponse])
def list_operation_logs(
    start: Optional[datetime] = Query(None, description="起始时间(含)"),
    end: Optional[datetime] = Query(None, description="结束时间(含)"),
    limit: int = Query(1000, ge=1, le=5000),
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    """查询时间范围内的操作日志（仅管理员），按发生时间倒序。"""
    return OperationLogService.query(db, start=start, end=end, limit=limit)
