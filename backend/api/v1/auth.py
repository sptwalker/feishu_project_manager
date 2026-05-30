import logging
from urllib.parse import urlencode
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from backend.api.deps import get_db
from backend.services.auth_service import AuthService, AuthenticationError
from backend.schemas.auth import Token, RefreshTokenRequest, FeishuCallbackParams
from backend.core.feishu import feishu_client
from backend.core.config import get_settings
from backend.core.dependencies import get_current_user
from backend.models.user import User

logger = logging.getLogger(__name__)

settings = get_settings()
router = APIRouter(prefix="/auth", tags=["authentication"])

@router.get("/feishu/login", response_class=RedirectResponse)
async def feishu_login():
    oauth_url = feishu_client.get_oauth_url()
    return RedirectResponse(url=oauth_url)

@router.get("/feishu/callback", response_class=RedirectResponse)
async def feishu_callback(
    params: FeishuCallbackParams = Depends(),
    db: Session = Depends(get_db)
):
    """飞书 OAuth 回调：换取 token 后重定向回前端并携带 token。

    前端 /auth/callback 路由会从 query 读取 token 存入本地并清理 URL。
    令牌经 query 传递，前端读取后立即 replace 清除历史；
    更高安全级别可改用 httpOnly Cookie（后续硬化项）。
    """
    frontend = settings.FRONTEND_URL.rstrip("/")
    try:
        result = await AuthService.feishu_login(db, params.code)
        query = urlencode({
            "access_token": result["access_token"],
            "refresh_token": result["refresh_token"],
        })
        return RedirectResponse(url=f"{frontend}/auth/callback?{query}")
    except AuthenticationError as e:
        logger.error(f"Authentication failed: {str(e)}")
        query = urlencode({"error": "authentication_failed"})
        return RedirectResponse(url=f"{frontend}/login?{query}")
    except Exception as e:
        logger.error(f"Unexpected error during authentication: {str(e)}")
        query = urlencode({"error": "server_error"})
        return RedirectResponse(url=f"{frontend}/login?{query}")

@router.post("/refresh", response_model=Token)
async def refresh_token(
    request: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    try:
        result = AuthService.refresh_access_token(db, request.refresh_token)
        return Token(
            access_token=result["access_token"],
            refresh_token=request.refresh_token,
            token_type=result["token_type"]
        )
    except ValueError as e:
        logger.error(f"Token refresh failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )

@router.post("/logout")
async def logout(current_user: User = Depends(get_current_user)):
    return {"message": "Logged out successfully. Please clear tokens on client side."}
