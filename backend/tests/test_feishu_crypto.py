import pytest
from backend.utils import feishu_crypto


def test_encrypt_decrypt_roundtrip():
    key = "test-encrypt-key-123"
    plain = '{"a":1,"中文":"值","list":[1,2,3]}'
    enc = feishu_crypto.encrypt(key, plain)
    assert isinstance(enc, str)
    assert feishu_crypto.decrypt(key, enc) == plain


def test_decrypt_empty_string():
    key = "k" * 16
    enc = feishu_crypto.encrypt(key, "")
    assert feishu_crypto.decrypt(key, enc) == ""


def test_decrypt_wrong_key_fails():
    enc = feishu_crypto.encrypt("right-key", "hello world payload")
    # 错误密钥要么解出乱码要么填充校验失败；这里断言不等于原文或抛错
    try:
        result = feishu_crypto.decrypt("wrong-key-xxxx", enc)
        assert result != "hello world payload"
    except (ValueError, UnicodeDecodeError):
        pass
