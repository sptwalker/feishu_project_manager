"""留言讨论区 API

公开（无内部鉴权；部分需外部 discuss token）：
- POST /discuss/code            发送邮箱验证码
- POST /discuss/register        注册（邮箱+验证码+昵称+手机号）→ 返回 token
- POST /discuss/login           登录（邮箱+验证码）→ 返回 token
- GET  /discuss/board           讨论区信息（开关关闭返回 closed）
- GET  /discuss/threads         楼列表（可见留言，分页）
- POST /discuss/messages        发留言/楼内补充（需外部 token）
- POST /discuss/upload          上传图片/视频（需外部 token）
- GET  /discuss/media/{name}    媒体文件（uuid 名防猜测）

内部（现有飞书 JWT）：
- GET  /discuss/admin/threads   全量列表（搜索/未回复/星级筛选，含用户资料）
- POST /discuss/admin/reply     回复某楼
- PUT  /discuss/admin/star      评定星级
- PUT  /discuss/admin/visibility 隐藏/恢复
- PUT  /discuss/admin/block     封禁/解封外部用户
"""
import os
import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, UploadFile, File, Request, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.api.deps import get_db
from backend.core.config import get_settings
from backend.core.dependencies import get_current_user, get_current_admin
from backend.models.user import User
from backend.services.settings_service import SettingsService
from backend.discuss.db import get_discuss_db
from backend.discuss.service import (
    DiscussService, DiscussError, create_ext_token, verify_ext_token,
)
from backend.discuss.models import DiscussUser

router = APIRouter()

# ---------- schemas（模块内自治，不进全局 schemas 包） ----------

class CodeRequest(BaseModel):
    email: str = Field(..., max_length=200)
    website: str = ""   # honeypot：正常用户永远为空，机器人常会填


class RegisterRequest(BaseModel):
    email: str = Field(..., max_length=200)
    code: str = Field(..., max_length=10)
    nickname: str = Field(..., max_length=50)
    phone: str = Field(..., max_length=30)
    website: str = ""   # honeypot


class LoginRequest(BaseModel):
    email: str = Field(..., max_length=200)
    code: str = Field(..., max_length=10)


class PostMessageRequest(BaseModel):
    content: str = Field(..., max_length=4000)
    thread_id: Optional[int] = None
    attachments: list = Field(default_factory=list)


# 附件硬上限（防超大 payload）；按类型的数量限额在 service 层权威判定
_MAX_ATTACHMENTS = 20


class AdminReplyRequest(BaseModel):
    thread_id: int
    content: str = Field(..., max_length=4000)


class StarRequest(BaseModel):
    message_id: int
    star: int = Field(..., ge=0, le=5)


class VisibilityRequest(BaseModel):
    message_id: int
    visible: bool


class BlockRequest(BaseModel):
    ext_user_id: int
    blocked: bool


class AnnouncementRequest(BaseModel):
    content: str = Field("", max_length=20000)   # markdown 源文


# ---------- 公共依赖 ----------

def _require_enabled(db: Session) -> None:
    """讨论区运行时开关：关闭时公开接口一律 404（不暴露功能存在）。"""
    if not SettingsService.get_discuss_enabled(db):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found")


def _ext_user(
    authorization: str = Header(""),
    ddb: Session = Depends(get_discuss_db),
) -> DiscussUser:
    """解析外部用户 token（Authorization: Bearer <discuss-token>）。"""
    token = authorization.replace("Bearer ", "").strip()
    uid = verify_ext_token(token) if token else None
    user = DiscussService.get_user(ddb, uid) if uid else None
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="请先登录")
    if user.status == "blocked":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="该账号已被限制使用")
    return user


def _raise(e: DiscussError):
    raise HTTPException(status_code=e.status_code, detail=e.message)


def _client_ip(request: Request) -> str:
    """真实客户端 IP：反代（nginx）后 request.client.host 只是代理 IP，会导致所有用户
    共用一个 IP、首个用户之后就误触发注册限流。优先取代理转发头。
    X-Forwarded-For 取最左（最初客户端），其次 X-Real-IP，最后回退直连 IP。"""
    xff = request.headers.get("x-forwarded-for", "")
    if xff.strip():
        return xff.split(",")[0].strip()
    xri = request.headers.get("x-real-ip", "").strip()
    if xri:
        return xri
    return request.client.host if request.client else ""


# ---------- 公开接口 ----------

@router.post("/discuss/code")
def request_code(
    payload: CodeRequest,
    db: Session = Depends(get_db),
    ddb: Session = Depends(get_discuss_db),
):
    """发送邮箱验证码（60s 冷却 / 每日≤10）。honeypot 命中静默成功（不给机器人信号）。"""
    _require_enabled(db)
    if payload.website:
        return {"ok": True}
    try:
        DiscussService.request_code(ddb, payload.email, SettingsService.get_smtp_config(db))
    except DiscussError as e:
        _raise(e)
    return {"ok": True}


@router.post("/discuss/register")
def register(
    payload: RegisterRequest,
    request: Request,
    db: Session = Depends(get_db),
    ddb: Session = Depends(get_discuss_db),
):
    """注册并登录：返回外部 token + 用户公开信息。"""
    _require_enabled(db)
    if payload.website:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="请求无效")
    ip = _client_ip(request)
    try:
        user = DiscussService.register(ddb, payload.email, payload.code,
                                       payload.nickname, payload.phone, ip)
    except DiscussError as e:
        _raise(e)
    return {"token": create_ext_token(user.id), "nickname": user.nickname, "email": user.email}


@router.post("/discuss/login")
def login(
    payload: LoginRequest,
    db: Session = Depends(get_db),
    ddb: Session = Depends(get_discuss_db),
):
    """登录：验证码通过即签发 token。"""
    _require_enabled(db)
    try:
        user = DiscussService.login(ddb, payload.email, payload.code)
    except DiscussError as e:
        _raise(e)
    return {"token": create_ext_token(user.id), "nickname": user.nickname, "email": user.email}


@router.get("/discuss/board")
def get_board(
    db: Session = Depends(get_db),
    ddb: Session = Depends(get_discuss_db),
):
    """讨论区信息（标题/欢迎语/开放状态）。开关关闭返回 enabled=False（公开页显示关闭提示）。"""
    if not SettingsService.get_discuss_enabled(db):
        return {"enabled": False}
    board = DiscussService.get_or_create_board(ddb)
    return {"enabled": True, "title": board.title,
            "welcome_text": board.welcome_text or "", "status": board.status,
            "announcement": SettingsService.get_discuss_announcement(db)}


@router.get("/discuss/threads")
def list_threads(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    ddb: Session = Depends(get_discuss_db),
    user: DiscussUser = Depends(_ext_user),
):
    """楼列表（需登录）：只返回当前用户自己发的楼 + 官方回复，看不到其他用户的内容。"""
    _require_enabled(db)
    return DiscussService.list_threads(
        ddb, page=page, size=size, include_hidden=False, ext_user_id=user.id)


@router.post("/discuss/messages")
def post_message(
    payload: PostMessageRequest,
    db: Session = Depends(get_db),
    ddb: Session = Depends(get_discuss_db),
    user: DiscussUser = Depends(_ext_user),
):
    """发留言（thread_id 为空开新楼；有值则限本人楼内补充）。附件须来自本站 /discuss/media。"""
    _require_enabled(db)
    # 附件白名单校验：仅允许本站 discuss 媒体 URL，防外链注入。
    # 硬上限只防超大 payload；按类型的数量限额由 service.post_message 权威判定并回友好错误。
    atts = []
    for a in (payload.attachments or [])[:_MAX_ATTACHMENTS]:
        if not isinstance(a, dict):
            continue
        url = str(a.get("url") or "")
        typ = str(a.get("type") or "")
        if typ in ("image", "video") and url.startswith("/api/v1/discuss/media/"):
            atts.append({"type": typ, "url": url,
                         "name": str(a.get("name") or "")[:100], "size": int(a.get("size") or 0)})
    try:
        msg = DiscussService.post_message(ddb, user, payload.content, atts, payload.thread_id)
    except DiscussError as e:
        _raise(e)
    return DiscussService._msg_public(msg)


# ---------- 媒体上传 / 访问 ----------

_IMG_EXT = {".jpg", ".jpeg", ".png"}
# 手机常见视频：mp4(通用) / mov·m4v(苹果) / 3gp(安卓旧) / webm(部分安卓)
_VID_EXT = {".mp4", ".mov", ".m4v", ".3gp", ".webm"}
# 魔数（文件头）校验：防改扩展名伪装（content-type 不可靠，故以文件头为准）
_IMG_MAGIC = {
    ".jpg": [b"\xff\xd8\xff"],
    ".png": [b"\x89PNG"],
}
# ISO-BMFF/QuickTime 家族(mp4/mov/m4v/3gp)：偏移 4-8 为首个 box 类型
_ISO_VID = {".mp4", ".mov", ".m4v", ".3gp"}
_ISO_BOX = {b"ftyp", b"moov", b"mdat", b"free", b"skip", b"wide", b"pnot"}
_EBML_HEAD = b"\x1aE\xdf\xa3"   # webm/mkv 的 EBML 头（偏移 0）
# 媒体访问时按扩展名回填 Content-Type，确保 <video> 能正确播放
_MEDIA_CT = {
    ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
    ".mp4": "video/mp4", ".mov": "video/quicktime", ".m4v": "video/x-m4v",
    ".3gp": "video/3gpp", ".webm": "video/webm",
}


def _media_dir() -> Path:
    d = Path(get_settings().DISCUSS_UPLOAD_DIR)
    d.mkdir(parents=True, exist_ok=True)
    return d


def _check_magic(ext: str, head: bytes) -> bool:
    """文件头魔数校验：ISO/QuickTime 家族看偏移 4-8 的 box 类型；webm 看 EBML 头；图片看头几字节。"""
    if ext in _ISO_VID:
        return len(head) >= 8 and head[4:8] in _ISO_BOX
    if ext == ".webm":
        return head.startswith(_EBML_HEAD)
    for m in _IMG_MAGIC.get(ext, []):
        if head.startswith(m):
            return True
    return False


@router.post("/discuss/upload")
async def upload_media(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: DiscussUser = Depends(_ext_user),
):
    """外部用户上传图片（JPG/PNG ≤10MB）或视频（MP4/MOV/M4V/3GP/WEBM ≤100MB）。仅注册用户可传（滥用防线）。"""
    _require_enabled(db)
    s = get_settings()
    ext = os.path.splitext(file.filename or "")[1].lower()
    # 类型按扩展名判定（白名单）；内容真伪由下方魔数校验把关。
    # 不再强卡 content-type：手机/各浏览器给视频的 content-type 五花八门
    # （video/mp4 / video/quicktime / application/octet-stream / 空），强卡会导致视频"经常失败"。
    if ext in _IMG_EXT:
        kind, max_bytes = "image", s.DISCUSS_IMAGE_MAX_MB * 1024 * 1024
    elif ext in _VID_EXT:
        kind, max_bytes = "video", s.DISCUSS_VIDEO_MAX_MB * 1024 * 1024
    else:
        raise HTTPException(status_code=400, detail="仅支持 JPG/PNG 图片或常见手机视频（MP4/MOV/M4V/3GP/WEBM）")
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="空文件")
    if len(data) > max_bytes:
        raise HTTPException(status_code=400,
                            detail=f"{'图片' if kind == 'image' else '视频'}不能超过 {max_bytes // (1024 * 1024)}MB")
    safe_ext = ".jpg" if ext == ".jpeg" else ext
    if not _check_magic(safe_ext, data[:16]):
        raise HTTPException(status_code=400, detail="文件内容与格式不符")
    fname = f"{uuid.uuid4().hex}{safe_ext}"
    (_media_dir() / fname).write_bytes(data)
    return {"type": kind, "url": f"/api/v1/discuss/media/{fname}",
            "name": file.filename or fname, "size": len(data)}


@router.get("/discuss/media/{filename}")
def get_media(filename: str):
    """媒体文件（不鉴权；uuid 文件名防猜测——同 PM 图片访问策略）。"""
    if "/" in filename or "\\" in filename or ".." in filename:
        raise HTTPException(status_code=400, detail="非法文件名")
    path = _media_dir() / filename
    if not path.is_file():
        raise HTTPException(status_code=404, detail="文件不存在")
    # 显式回填 Content-Type（尤其 .mov/.3gp，mimetypes 未必识别），保证 <video> 正常播放
    ext = os.path.splitext(filename)[1].lower()
    return FileResponse(path, media_type=_MEDIA_CT.get(ext))


# ---------- 内部接口（现有飞书 JWT） ----------

@router.get("/discuss/admin/threads")
def admin_list_threads(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=50),
    keyword: str = Query(""),
    only_unreplied: bool = Query(False),
    min_star: int = Query(0, ge=0, le=5),
    ddb: Session = Depends(get_discuss_db),
    current_user: User = Depends(get_current_user),
):
    """内部楼列表：含隐藏与用户资料；支持搜索（内容/昵称/邮箱/手机）、未回复筛选、星级过滤。"""
    return DiscussService.list_threads(
        ddb, page=page, size=size, include_hidden=True,
        only_unreplied=only_unreplied, keyword=keyword, min_star=min_star,
    )


@router.post("/discuss/admin/reply")
def admin_reply(
    payload: AdminReplyRequest,
    ddb: Session = Depends(get_discuss_db),
    current_user: User = Depends(get_current_user),
):
    """内部回复某楼（对外显示英文名 + 官方徽章；楼标记为已回复）。"""
    try:
        # 对外公开页展示英文名（name_en）；未设置英文名时回退中文名
        author = (current_user.name_en or "").strip() or current_user.name
        msg = DiscussService.internal_reply(ddb, payload.thread_id, author, payload.content)
    except DiscussError as e:
        _raise(e)
    return DiscussService._msg_public(msg)


@router.put("/discuss/admin/star")
def admin_star(
    payload: StarRequest,
    ddb: Session = Depends(get_discuss_db),
    current_user: User = Depends(get_current_user),
):
    """评定奖励星级（0-5；0=取消）。"""
    try:
        msg = DiscussService.set_star(ddb, payload.message_id, payload.star)
    except DiscussError as e:
        _raise(e)
    return {"id": msg.id, "star": msg.star}


@router.put("/discuss/admin/visibility")
def admin_visibility(
    payload: VisibilityRequest,
    ddb: Session = Depends(get_discuss_db),
    current_user: User = Depends(get_current_user),
):
    """隐藏 / 恢复留言（先发后审的事后管控）。"""
    try:
        msg = DiscussService.set_visibility(ddb, payload.message_id, payload.visible)
    except DiscussError as e:
        _raise(e)
    return {"id": msg.id, "status": msg.status}


@router.put("/discuss/admin/block")
def admin_block(
    payload: BlockRequest,
    ddb: Session = Depends(get_discuss_db),
    current_user: User = Depends(get_current_user),
):
    """封禁 / 解封外部用户（封禁后不能发帖/上传/登录）。"""
    try:
        user = DiscussService.set_user_blocked(ddb, payload.ext_user_id, payload.blocked)
    except DiscussError as e:
        _raise(e)
    return {"id": user.id, "status": user.status}


@router.put("/discuss/admin/announcement")
def admin_set_announcement(
    payload: AnnouncementRequest,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    """设置留言区公告（markdown 源文）。仅 PMS 管理员；公开页顶部展示。"""
    SettingsService.set_discuss_announcement(db, payload.content)
    return {"content": SettingsService.get_discuss_announcement(db)}
