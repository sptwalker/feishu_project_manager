import json
import time
import httpx
from typing import Optional, Dict, Any, List
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
        # tenant_access_token 缓存
        self._tenant_token: Optional[str] = None
        self._tenant_token_expire_at: float = 0.0

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

    async def get_tenant_access_token(self) -> str:
        """获取并缓存 tenant_access_token（发送消息、操作多维表格使用）"""
        now = time.monotonic()
        if self._tenant_token and now < self._tenant_token_expire_at:
            return self._tenant_token

        client = self._get_client()
        try:
            response = await client.post(
                f"{self.BASE_URL}/auth/v3/tenant_access_token/internal",
                json={"app_id": self.app_id, "app_secret": self.app_secret},
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise FeishuAuthError(f"HTTP error getting tenant access token: {e}")
        except httpx.RequestError as e:
            raise FeishuAPIError(f"Request error getting tenant access token: {e}")

        data = response.json()
        if data.get("code") != 0:
            raise FeishuAuthError(f"Failed to get tenant access token: {data.get('msg')}")

        self._tenant_token = data["tenant_access_token"]
        # 提前 60 秒过期，避免边界失效
        self._tenant_token_expire_at = now + max(0, int(data.get("expire", 7200)) - 60)
        return self._tenant_token

    async def _post_authed(self, path: str, json_body: Dict[str, Any],
                           params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """以 tenant_access_token 发送 POST 请求并解析飞书响应"""
        token = await self.get_tenant_access_token()
        client = self._get_client()
        try:
            response = await client.post(
                f"{self.BASE_URL}{path}",
                headers={"Authorization": f"Bearer {token}",
                         "Content-Type": "application/json; charset=utf-8"},
                params=params,
                json=json_body,
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise FeishuAPIError(f"HTTP error on POST {path}: {e}")
        except httpx.RequestError as e:
            raise FeishuAPIError(f"Request error on POST {path}: {e}")

        data = response.json()
        if data.get("code") != 0:
            raise FeishuAPIError(f"Feishu API error on POST {path}: {data.get('msg')}")
        return data.get("data", {})

    async def create_document(self, title: str) -> str:
        """创建飞书云文档（docx），返回 document_id。需要 docx:document 权限。"""
        data = await self._post_authed(
            "/docx/v1/documents",
            json_body={"title": title[:800]},
        )
        doc = data.get("document", {})
        document_id = doc.get("document_id")
        if not document_id:
            raise FeishuAPIError("create_document 未返回 document_id")
        return document_id

    @staticmethod
    def _run(content: str, bold: bool = False, color: Optional[int] = None) -> Dict[str, Any]:
        """构造一个 text_run 文本片段，可加粗/上色。color 为飞书字体色枚举(1-7)。"""
        run: Dict[str, Any] = {"text_run": {"content": content}}
        style: Dict[str, Any] = {}
        if bold:
            style["bold"] = True
        if color:
            style["text_color"] = color
        if style:
            run["text_run"]["text_element_style"] = style
        return run

    @staticmethod
    def text_block(content: str) -> Dict[str, Any]:
        """构造一个文本段落块（block_type=2）"""
        return {
            "block_type": 2,
            "text": {"elements": [FeishuClient._run(content)]},
        }

    @staticmethod
    def rich_block(runs: List[tuple]) -> Dict[str, Any]:
        """构造含多片段的文本段落块。runs: [(content, bold?, color?), ...]"""
        els = []
        for r in runs:
            content = r[0]
            bold = r[1] if len(r) > 1 else False
            color = r[2] if len(r) > 2 else None
            els.append(FeishuClient._run(content, bold, color))
        return {"block_type": 2, "text": {"elements": els}}

    @staticmethod
    def heading_block(content: str, level: int = 1) -> Dict[str, Any]:
        """构造标题块。level 1/2/3 → heading1/2/3（block_type 3/4/5）"""
        bt = {1: 3, 2: 4, 3: 5}.get(level, 3)
        key = f"heading{level}"
        return {"block_type": bt, key: {"elements": [FeishuClient._run(content)]}}

    async def append_document_blocks(self, document_id: str,
                                     blocks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """向文档根节点追加块（block_id 用 document_id 表示根）。需要 docx:document 权限。"""
        return await self._post_authed(
            f"/docx/v1/documents/{document_id}/blocks/{document_id}/children",
            json_body={"children": blocks},
        )

    async def send_message(self, receive_id: str, msg_type: str, content: Dict[str, Any],
                           receive_id_type: str = "user_id") -> Dict[str, Any]:
        """发送消息（im/v1/messages），content 会被序列化为 JSON 字符串"""
        return await self._post_authed(
            "/im/v1/messages",
            params={"receive_id_type": receive_id_type},
            json_body={
                "receive_id": receive_id,
                "msg_type": msg_type,
                "content": json.dumps(content, ensure_ascii=False),
            },
        )

    async def send_text(self, receive_id: str, text: str,
                        receive_id_type: str = "user_id") -> Dict[str, Any]:
        """发送纯文本消息"""
        return await self.send_message(receive_id, "text", {"text": text}, receive_id_type)

    async def send_card(self, receive_id: str, card: Dict[str, Any],
                        receive_id_type: str = "user_id") -> Dict[str, Any]:
        """发送交互式卡片消息"""
        return await self.send_message(receive_id, "interactive", card, receive_id_type)

    async def bitable_list_records(self, app_token: str, table_id: str,
                                   page_size: int = 100,
                                   filter_expr: Optional[str] = None) -> List[Dict[str, Any]]:
        """列出多维表格记录"""
        token = await self.get_tenant_access_token()
        client = self._get_client()
        params: Dict[str, Any] = {"page_size": page_size}
        if filter_expr:
            params["filter"] = filter_expr
        try:
            response = await client.get(
                f"{self.BASE_URL}/bitable/v1/apps/{app_token}/tables/{table_id}/records",
                headers={"Authorization": f"Bearer {token}"},
                params=params,
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise FeishuAPIError(f"HTTP error listing bitable records: {e}")
        except httpx.RequestError as e:
            raise FeishuAPIError(f"Request error listing bitable records: {e}")

        data = response.json()
        if data.get("code") != 0:
            raise FeishuAPIError(f"Failed to list bitable records: {data.get('msg')}")
        return data.get("data", {}).get("items", []) or []

    async def bitable_create_record(self, app_token: str, table_id: str,
                                    fields: Dict[str, Any]) -> Dict[str, Any]:
        """创建多维表格记录"""
        return await self._post_authed(
            f"/bitable/v1/apps/{app_token}/tables/{table_id}/records",
            json_body={"fields": fields},
        )

    async def bitable_update_record(self, app_token: str, table_id: str,
                                    record_id: str, fields: Dict[str, Any]) -> Dict[str, Any]:
        """更新多维表格记录"""
        token = await self.get_tenant_access_token()
        client = self._get_client()
        try:
            response = await client.put(
                f"{self.BASE_URL}/bitable/v1/apps/{app_token}/tables/{table_id}/records/{record_id}",
                headers={"Authorization": f"Bearer {token}",
                         "Content-Type": "application/json; charset=utf-8"},
                json={"fields": fields},
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise FeishuAPIError(f"HTTP error updating bitable record: {e}")
        except httpx.RequestError as e:
            raise FeishuAPIError(f"Request error updating bitable record: {e}")

        data = response.json()
        if data.get("code") != 0:
            raise FeishuAPIError(f"Failed to update bitable record: {data.get('msg')}")
        return data.get("data", {})


# 全局飞书客户端实例
feishu_client = FeishuClient()
