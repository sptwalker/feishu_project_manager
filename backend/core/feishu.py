import httpx
from typing import Optional, Dict, Any
from urllib.parse import quote
from backend.core.config import get_settings

settings = get_settings()


class FeishuAPIError(Exception):
    """飞书 API 错误"""
    pass


class FeishuAuthError(FeishuAPIError):
    """飞书认证错误"""
    pass


class FeishuClient:
    """飞书 API 客户端"""

    BASE_URL = "https://open.feishu.cn/open-apis"

    def __init__(self):
        self.app_id = settings.FEISHU_APP_ID
        self.app_secret = settings.FEISHU_APP_SECRET
        self._client: Optional[httpx.AsyncClient] = None

    def _get_client(self) -> httpx.AsyncClient:
        """获取或创建 HTTP 客户端"""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    async def close(self):
        """关闭 HTTP 客户端"""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def get_app_access_token(self) -> str:
        """获取应用 access token"""
        client = self._get_client()
        try:
            response = await client.post(
                f"{self.BASE_URL}/auth/v3/app_access_token/internal",
                json={
                    "app_id": self.app_id,
                    "app_secret": self.app_secret
                }
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise FeishuAuthError(f"HTTP error getting app access token: {e}")
        except httpx.RequestError as e:
            raise FeishuAPIError(f"Request error getting app access token: {e}")

        data = response.json()
        if data.get("code") != 0:
            raise FeishuAuthError(f"Failed to get app access token: {data.get('msg')}")
        return data["app_access_token"]

    async def get_user_access_token(self, code: str) -> Dict[str, Any]:
        """通过 authorization code 获取用户 access token"""
        app_token = await self.get_app_access_token()

        client = self._get_client()
        try:
            response = await client.post(
                f"{self.BASE_URL}/authen/v1/access_token",
                headers={"Authorization": f"Bearer {app_token}"},
                json={"grant_type": "authorization_code", "code": code}
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise FeishuAuthError(f"HTTP error getting user access token: {e}")
        except httpx.RequestError as e:
            raise FeishuAPIError(f"Request error getting user access token: {e}")

        data = response.json()
        if data.get("code") != 0:
            raise FeishuAuthError(f"Failed to get user access token: {data.get('msg')}")
        return data["data"]

    async def get_user_info(self, user_access_token: str) -> Dict[str, Any]:
        """获取用户信息"""
        client = self._get_client()
        try:
            response = await client.get(
                f"{self.BASE_URL}/authen/v1/user_info",
                headers={"Authorization": f"Bearer {user_access_token}"}
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise FeishuAuthError(f"HTTP error getting user info: {e}")
        except httpx.RequestError as e:
            raise FeishuAPIError(f"Request error getting user info: {e}")

        data = response.json()
        if data.get("code") != 0:
            raise FeishuAPIError(f"Failed to get user info: {data.get('msg')}")
        return data["data"]

    def get_oauth_url(self, state: Optional[str] = None) -> str:
        """生成飞书 OAuth 授权 URL"""
        redirect_uri = quote(settings.FEISHU_REDIRECT_URI)
        url = f"https://open.feishu.cn/open-apis/authen/v1/authorize?app_id={self.app_id}&redirect_uri={redirect_uri}"
        if state:
            url += f"&state={quote(state)}"
        return url

# 全局飞书客户端实例
feishu_client = FeishuClient()
