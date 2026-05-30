"""飞书事件订阅加解密工具

飞书开放平台对事件回调采用 AES-256-CBC 加密：
- key = sha256(encrypt_key)
- 数据 = base64(IV(16字节) + 密文)，PKCS7 填充
参考：https://open.feishu.cn/document/事件订阅/加密
"""
import base64
import hashlib
import os
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes


def _derive_key(encrypt_key: str) -> bytes:
    return hashlib.sha256(encrypt_key.encode("utf-8")).digest()


def decrypt(encrypt_key: str, encrypt: str) -> str:
    """解密飞书事件回调的 encrypt 字段，返回明文 JSON 字符串"""
    key = _derive_key(encrypt_key)
    raw = base64.b64decode(encrypt)
    iv, ciphertext = raw[:16], raw[16:]
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
    decryptor = cipher.decryptor()
    padded = decryptor.update(ciphertext) + decryptor.finalize()
    if not padded:
        return ""
    pad_len = padded[-1]
    if pad_len < 1 or pad_len > 16:
        raise ValueError("Invalid padding")
    return padded[:-pad_len].decode("utf-8")


def encrypt(encrypt_key: str, plaintext: str) -> str:
    """加密明文（主要用于测试与本地验证），返回 base64 字符串"""
    key = _derive_key(encrypt_key)
    iv = os.urandom(16)
    data = plaintext.encode("utf-8")
    pad_len = 16 - (len(data) % 16)
    padded = data + bytes([pad_len]) * pad_len
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
    encryptor = cipher.encryptor()
    ciphertext = encryptor.update(padded) + encryptor.finalize()
    return base64.b64encode(iv + ciphertext).decode("utf-8")
