"""数据库全量导出 / 导入 API（仅管理员）"""
import json

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.responses import Response
from sqlalchemy.orm import Session

from backend.api.deps import get_db
from backend.core.dependencies import get_current_admin
from backend.core.config import get_settings
from backend.models.user import User
from backend.services.backup_service import BackupService

router = APIRouter()


@router.get("/backup/export")
def export_backup(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    """导出全部业务数据为 JSON 快照文件（仅管理员）"""
    settings = get_settings()
    snapshot = BackupService.export_all(db, app_version=settings.APP_VERSION)
    content = json.dumps(snapshot, ensure_ascii=False, indent=2).encode("utf-8")
    ts = snapshot["exported_at"].replace(":", "").replace("-", "").replace("T", "_")[:15]
    filename = f"feishu_pm_backup_{ts}.json"
    return Response(
        content=content,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/backup/import")
async def import_backup(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    """上传 JSON 快照，全量替换导入（仅管理员）。返回各表导入行数。"""
    raw = await file.read()
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="文件不是有效的 JSON")
    try:
        counts = BackupService.import_all(db, payload)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="导入失败，已回滚，原数据未受影响",
        )
    return {"message": "导入成功", "counts": counts}
