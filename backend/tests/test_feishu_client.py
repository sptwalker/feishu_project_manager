import asyncio
import json
import httpx
import pytest
from backend.core.feishu import FeishuClient, FeishuAPIError


def _client(handler):
    c = FeishuClient()
    c.app_id = "app"
    c.app_secret = "secret"
    c._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return c


def test_get_tenant_access_token():
    def handler(request):
        assert request.url.path.endswith("/auth/v3/tenant_access_token/internal")
        return httpx.Response(200, json={"code": 0, "tenant_access_token": "t-1", "expire": 7200})
    c = _client(handler)
    assert asyncio.run(c.get_tenant_access_token()) == "t-1"


def test_tenant_token_is_cached():
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        return httpx.Response(200, json={"code": 0, "tenant_access_token": "t-1", "expire": 7200})
    c = _client(handler)
    asyncio.run(c.get_tenant_access_token())
    asyncio.run(c.get_tenant_access_token())
    assert calls["n"] == 1


def test_tenant_token_error_on_nonzero_code():
    def handler(request):
        return httpx.Response(200, json={"code": 99, "msg": "bad"})
    c = _client(handler)
    with pytest.raises(FeishuAPIError):
        asyncio.run(c.get_tenant_access_token())


def test_send_text():
    seen = {}

    def handler(request):
        if request.url.path.endswith("/tenant_access_token/internal"):
            return httpx.Response(200, json={"code": 0, "tenant_access_token": "t", "expire": 7200})
        if request.url.path.endswith("/im/v1/messages"):
            seen["params"] = dict(request.url.params)
            seen["body"] = json.loads(request.content)
            return httpx.Response(200, json={"code": 0, "data": {"message_id": "m1"}})
        return httpx.Response(404, json={"code": 1, "msg": "nf"})
    c = _client(handler)
    data = asyncio.run(c.send_text("u123", "hello"))
    assert data["message_id"] == "m1"
    assert seen["params"]["receive_id_type"] == "user_id"
    assert seen["body"]["msg_type"] == "text"
    assert json.loads(seen["body"]["content"]) == {"text": "hello"}


def test_send_card():
    seen = {}

    def handler(request):
        if request.url.path.endswith("/tenant_access_token/internal"):
            return httpx.Response(200, json={"code": 0, "tenant_access_token": "t", "expire": 7200})
        if request.url.path.endswith("/im/v1/messages"):
            seen["body"] = json.loads(request.content)
            return httpx.Response(200, json={"code": 0, "data": {"message_id": "m2"}})
        return httpx.Response(404, json={"code": 1})
    c = _client(handler)
    card = {"header": {"title": {"tag": "plain_text", "content": "T"}}}
    data = asyncio.run(c.send_card("u1", card))
    assert data["message_id"] == "m2"
    assert seen["body"]["msg_type"] == "interactive"


def test_bitable_create_record():
    def handler(request):
        if request.url.path.endswith("/tenant_access_token/internal"):
            return httpx.Response(200, json={"code": 0, "tenant_access_token": "t", "expire": 7200})
        if request.url.path.endswith("/records") and request.method == "POST":
            return httpx.Response(200, json={"code": 0, "data": {"record": {"record_id": "rec1"}}})
        return httpx.Response(404, json={"code": 1})
    c = _client(handler)
    data = asyncio.run(c.bitable_create_record("app", "tbl", {"x": 1}))
    assert data["record"]["record_id"] == "rec1"


def test_bitable_update_record():
    def handler(request):
        if request.url.path.endswith("/tenant_access_token/internal"):
            return httpx.Response(200, json={"code": 0, "tenant_access_token": "t", "expire": 7200})
        if "/records/" in request.url.path and request.method == "PUT":
            return httpx.Response(200, json={"code": 0, "data": {"record": {"record_id": "rec1"}}})
        return httpx.Response(404, json={"code": 1})
    c = _client(handler)
    data = asyncio.run(c.bitable_update_record("app", "tbl", "rec1", {"x": 2}))
    assert data["record"]["record_id"] == "rec1"


def test_bitable_list_records():
    def handler(request):
        if request.url.path.endswith("/tenant_access_token/internal"):
            return httpx.Response(200, json={"code": 0, "tenant_access_token": "t", "expire": 7200})
        if request.url.path.endswith("/records") and request.method == "GET":
            return httpx.Response(200, json={"code": 0, "data": {"items": [{"record_id": "r1"}]}})
        return httpx.Response(404, json={"code": 1})
    c = _client(handler)
    items = asyncio.run(c.bitable_list_records("app", "tbl"))
    assert items == [{"record_id": "r1"}]


def test_send_message_api_error():
    def handler(request):
        if request.url.path.endswith("/tenant_access_token/internal"):
            return httpx.Response(200, json={"code": 0, "tenant_access_token": "t", "expire": 7200})
        return httpx.Response(200, json={"code": 230002, "msg": "forbidden"})
    c = _client(handler)
    with pytest.raises(FeishuAPIError):
        asyncio.run(c.send_text("u1", "hi"))
