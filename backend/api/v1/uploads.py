"""图片上传 / 访问（进展详情配图）

- POST /uploads/image：上传 JPG/PNG（≤10MB），存到 UPLOAD_DIR，返回 {url, name, size}。
  鉴权：管理员 / 项目经理。
- GET /uploads/{filename}：返回图片文件（FileResponse）。不鉴权——<img> 标签无法携带
  登录 token，用 uuid 文件名作防猜测保护（同类系统常见做法）。
"""
import os
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from fastapi.responses import FileResponse

from backend.core.config import get_settings
from backend.core.dependencies import get_current_user
from backend.core.permissions import PermissionChecker
from backend.models.user import User

router = APIRouter()

# 允许的图片类型：扩展名 + content-type 双校验
_ALLOWED_EXT = {".jpg", ".jpeg", ".png"}
_ALLOWED_CT = {"image/jpeg", "image/png"}


def _upload_dir() -> Path:
    """上传目录（不存在则创建）。"""
    d = Path(get_settings().UPLOAD_DIR)
    d.mkdir(parents=True, exist_ok=True)
    return d


@router.post("/uploads/image")
async def upload_image(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """上传进展配图（管理员 / 项目经理）。校验 JPG/PNG + ≤10MB，返回可访问 URL。"""
    if not PermissionChecker.can_manage(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无上传权限")
    # 1. 扩展名 + content-type 双校验
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in _ALLOWED_EXT or (file.content_type or "") not in _ALLOWED_CT:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="仅支持 JPG / PNG 格式图片")
    # 2. 读内容并校验大小（后端强校验，防前端绕过）
    data = await file.read()
    max_bytes = get_settings().UPLOAD_MAX_BYTES
    if not data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="空文件")
    if len(data) > max_bytes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"图片不能超过 {max_bytes // (1024 * 1024)}MB")
    # 3. uuid 文件名（防路径穿越 / 冲突），jpeg 归一为 jpg
    safe_ext = ".jpg" if ext == ".jpeg" else ext
    fname = f"{uuid.uuid4().hex}{safe_ext}"
    (_upload_dir() / fname).write_bytes(data)
    return {
        "url": f"/api/v1/uploads/{fname}",
        "name": file.filename or fname,
        "size": len(data),
    }


@router.get("/uploads/{filename}")
def get_image(filename: str):
    """返回上传的图片文件（不鉴权；uuid 文件名作防猜测保护）。"""
    # 防路径穿越：拒绝任何含路径分隔符或上跳的文件名
    if "/" in filename or "\\" in filename or ".." in filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="非法文件名")
    path = _upload_dir() / filename
    if not path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="图片不存在")
    return FileResponse(path)
