"""飞书事件订阅 Webhook 接收端点

处理飞书开放平台的事件回调：
- url_verification：返回 challenge 完成 URL 校验
- 加密事件：用 FEISHU_ENCRYPT_KEY 解密后再处理
- 校验 verification token，分发事件

参考：https://open.feishu.cn/document/事件订阅
"""
import json
import logging
from fastapi import APIRouter, Request, HTTPException, status
from backend.core.config import get_settings
from backend.utils import feishu_crypto

logger = logging.getLogger(__name__)
router = APIRouter()


def _parse_body(raw: dict) -> dict:
    """若为加密事件则解密，否则原样返回"""
    settings = get_settings()
    if "encrypt" in raw:
        if not settings.FEISHU_ENCRYPT_KEY:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Encrypted event received but FEISHU_ENCRYPT_KEY is not configured",
            )
        try:
            plaintext = feishu_crypto.decrypt(settings.FEISHU_ENCRYPT_KEY, raw["encrypt"])
            return json.loads(plaintext)
        except Exception as e:
            logger.warning(f"Failed to decrypt Feishu event: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to decrypt event",
            )
    return raw


def _verify_token(body: dict) -> None:
    """校验 verification token（v1 在顶层 token，v2 在 header.token）"""
    settings = get_settings()
    expected = settings.FEISHU_VERIFICATION_TOKEN
    if not expected:
        # 未配置则跳过校验（开发环境）
        return
    token = body.get("token")
    if token is None:
        token = (body.get("header") or {}).get("token")
    if token != expected:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid verification token",
        )


def _dispatch_event(body: dict) -> None:
    """分发事件（当前仅记录日志，后续可接入业务处理）"""
    event_type = (body.get("header") or {}).get("event_type") or body.get("type")
    logger.info(f"Received Feishu event: {event_type}")


@router.post("/feishu/webhook")
async def feishu_webhook(request: Request):
    """飞书事件回调入口"""
    raw = await request.json()
    body = _parse_body(raw)

    # URL 校验握手
    if body.get("type") == "url_verification":
        _verify_token(body)
        return {"challenge": body.get("challenge", "")}

    # 普通事件
    _verify_token(body)
    _dispatch_event(body)
    return {"code": 0, "msg": "success"}
