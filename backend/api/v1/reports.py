"""报表与导入导出 API

- 仪表盘统计与项目进度
- 项目/任务 Excel 导出（附件下载）
- 任务 Excel 导入（上传）
"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.responses import Response
from sqlalchemy.orm import Session
from backend.api.deps import get_db
from backend.core.dependencies import get_current_user
from backend.models.user import User
from backend.services.statistics_service import StatisticsService
from backend.services.export_service import ExportService
from backend.services.import_service import ImportService
from backend.services.project_service import ProjectService
from backend.utils.excel import ExcelParseError
from backend.core.permissions import PermissionChecker
from backend.schemas.statistics import (
    DashboardResponse, ProjectProgressResponse, ImportResultResponse,
)

router = APIRouter()

XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _xlsx_response(content: bytes, filename: str) -> Response:
    return Response(
        content=content,
        media_type=XLSX_MEDIA_TYPE,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _get_project_or_404(db: Session, project_id: int):
    project = ProjectService.get_by_id(db, project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


@router.get("/statistics/dashboard", response_model=DashboardResponse)
def get_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取仪表盘统计数据"""
    return StatisticsService.dashboard(db)


@router.get("/statistics/projects/{project_id}/progress", response_model=ProjectProgressResponse)
def get_project_progress(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取单个项目的进度统计"""
    result = StatisticsService.project_progress(db, project_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return result


@router.get("/reports/projects/export")
def export_projects(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """导出全部项目为 Excel"""
    content = ExportService.export_projects(db)
    return _xlsx_response(content, "projects.xlsx")


@router.get("/reports/projects/{project_id}/tasks/export")
def export_project_tasks(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """导出指定项目的任务为 Excel"""
    _get_project_or_404(db, project_id)
    content = ExportService.export_tasks(db, project_id)
    return _xlsx_response(content, f"project_{project_id}_tasks.xlsx")


@router.post("/reports/projects/{project_id}/tasks/import", response_model=ImportResultResponse)
async def import_project_tasks(
    project_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """从 Excel 导入任务到指定项目"""
    project = _get_project_or_404(db, project_id)
    PermissionChecker.require_project_permission(current_user, project, "modify")

    data = await file.read()
    try:
        result = ImportService.import_tasks(db, project_id, data)
    except ExcelParseError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return result.to_dict()


@router.post("/reports/projects/import", response_model=ImportResultResponse)
async def import_projects(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """从 Excel（周会跟进清单格式）批量导入项目"""
    data = await file.read()
    try:
        result = ImportService.import_projects(db, data)
    except ExcelParseError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return result.to_dict()
