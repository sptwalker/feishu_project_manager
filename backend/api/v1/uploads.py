"""图片 / 视频上传 / 访问（进展详情配图、配视频）

- POST /uploads/image：上传 JPG/PNG（≤10MB），存到 UPLOAD_DIR，返回 {url, name, size}。
  鉴权：管理员 / 项目经理。
- POST /uploads/video：上传 MP4/MOV/M4V/3GP/WEBM（≤100MB），同上目录，返回 {url, name, size}。
- GET /uploads/{filename}：返回文件（FileResponse）。不鉴权——<img>/<video> 标签无法携带
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

# 视频：扩展名白名单 + 文件头(魔数)校验；不信任 content-type（手机视频 CT 混乱，做法同留言区）。
_VID_EXT = {".mp4", ".mov", ".m4v", ".3gp", ".webm"}
_ISO_VID = {".mp4", ".mov", ".m4v", ".3gp"}          # ISO-BMFF/QuickTime 家族：偏移 4-8 为首个 box 类型
_ISO_BOX = {b"ftyp", b"moov", b"mdat", b"free", b"skip", b"wide", b"pnot"}
_EBML_HEAD = b"\x1aE\xdf\xa3"                          # webm/mkv 的 EBML 头（偏移 0）
# serve 时按扩展名回填 Content-Type：.mov/.m4v/.3gp mimetypes 常解析不出，<video> 才能正确播放
_VIDEO_CT = {
    ".mp4": "video/mp4", ".mov": "video/quicktime", ".m4v": "video/x-m4v",
    ".3gp": "video/3gpp", ".webm": "video/webm",
}


def _check_video_magic(ext: str, head: bytes) -> bool:
    """视频文件头校验：防改扩展名伪装（首 16 字节）。"""
    if ext in _ISO_VID:
        return len(head) >= 8 and head[4:8] in _ISO_BOX
    if ext == ".webm":
        return head.startswith(_EBML_HEAD)
    return False


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


@router.post("/uploads/video")
async def upload_video(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """上传进展视频（管理员 / 项目经理）。校验扩展名 + 文件头 + ≤100MB，返回可访问 URL。"""
    if not PermissionChecker.can_manage(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无上传权限")
    # 1. 扩展名白名单（不信任 content-type：手机视频 CT 混乱）
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in _VID_EXT:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="仅支持常见视频（MP4/MOV/M4V/3GP/WEBM）")
    # 2. 读内容并校验大小（后端强校验，防前端绕过）
    data = await file.read()
    max_bytes = get_settings().UPLOAD_VIDEO_MAX_BYTES
    if not data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="空文件")
    if len(data) > max_bytes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"视频不能超过 {max_bytes // (1024 * 1024)}MB")
    # 3. 文件头校验：防改扩展名伪装
    if not _check_video_magic(ext, data[:16]):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="文件内容与格式不符")
    fname = f"{uuid.uuid4().hex}{ext}"
    (_upload_dir() / fname).write_bytes(data)
    return {
        "url": f"/api/v1/uploads/{fname}",
        "name": file.filename or fname,
        "size": len(data),
    }


@router.get("/uploads/{filename}")
def get_image(filename: str):
    """返回上传的图片/视频文件（不鉴权；uuid 文件名作防猜测保护）。"""
    # 防路径穿越：拒绝任何含路径分隔符或上跳的文件名
    if "/" in filename or "\\" in filename or ".." in filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="非法文件名")
    path = _upload_dir() / filename
    if not path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文件不存在")
    # 视频回填 Content-Type（.mov/.m4v/.3gp mimetypes 常解析不出）；图片 None→FileResponse 自动识别
    ext = os.path.splitext(filename)[1].lower()
    return FileResponse(path, media_type=_VIDEO_CT.get(ext))
