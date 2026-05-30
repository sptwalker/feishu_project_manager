from pydantic import BaseModel, Field
from typing import Optional, Literal

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = "bearer"

class TokenPayload(BaseModel):
    sub: Optional[int] = None
    exp: Optional[int] = None
    type: Optional[str] = None

class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(..., description="Refresh token")

class FeishuCallbackParams(BaseModel):
    code: str = Field(..., min_length=1, description="Authorization code")
    state: Optional[str] = Field(None, description="State parameter")
