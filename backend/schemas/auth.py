from pydantic import BaseModel, Field
from typing import Optional

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class TokenPayload(BaseModel):
    sub: Optional[int] = None
    exp: Optional[int] = None
    type: Optional[str] = None

class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(..., description="Refresh token")

class FeishuCallbackParams(BaseModel):
    code: str = Field(..., description="Authorization code")
    state: Optional[str] = Field(None, description="State parameter")
