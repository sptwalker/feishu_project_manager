from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from backend.api.deps import get_db
from backend.services.auth_service import AuthService
from backend.schemas.auth import Token, RefreshTokenRequest, FeishuCallbackParams
from backend.core.feishu import feishu_client
from backend.core.config import get_settings

settings = get_settings()
router = APIRouter(prefix="/auth", tags=["authentication"])

@router.get("/feishu/login")
async def feishu_login():
    oauth_url = feishu_client.get_oauth_url()
    return RedirectResponse(url=oauth_url)

@router.get("/feishu/callback", response_model=Token)
async def feishu_callback(
    code: str,
    state: str = None,
    db: Session = Depends(get_db)
):
    try:
        result = await AuthService.feishu_login(db, code)
        return Token(
            access_token=result["access_token"],
            refresh_token=result["refresh_token"],
            token_type=result["token_type"]
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Login failed: {str(e)}"
        )

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
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )

@router.post("/logout")
async def logout():
    return {"message": "Logged out successfully"}
