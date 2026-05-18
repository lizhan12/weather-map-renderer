import base64
import hashlib
import json
import time

from gmalglib.sm4 import SM4


def sm4_decode(key: str, data: str) -> dict:
    """使用 SM4 ECB 模式解密 Base64 编码的密文, 返回 JSON 字典.

    Args:
        key: 加密密钥, 取前 16 字节作为 SM4 密钥
        data: Base64 编码的 SM4 加密数据

    Returns:
        解密后的 JSON 字典
    """
    key_bytes = key.encode()[:16]
    encrypted_data = base64.b64decode(data)
    sm4 = SM4(key_bytes)
    n_blocks = len(encrypted_data) // 16
    decrypted = bytearray()
    for i in range(n_blocks):
        decrypted.extend(sm4.decrypt(bytes(encrypted_data[i * 16 : (i + 1) * 16])))
    pad_len = decrypted[-1]
    if 1 <= pad_len <= 16:
        decrypted = decrypted[:-pad_len]
    return json.loads(decrypted.decode())


def sign_encode(key: str, secret: str) -> tuple[str, str]:
    """生成 MD5 签名和时间戳, 用于接口鉴权.

    签名算法: md5(key + secret + timestamp)

    Args:
        key: 应用密钥 (appKey)
        secret: 签名密钥 (appSecret)

    Returns:
        (md5_hex, timestamp_ms) 元组, key 为空时返回 ("", "")
    """
    if not key:
        return "", ""
    md5_hash = hashlib.md5()
    timestr = str(int(time.time() * 1000))
    md5_hash.update((key + secret + timestr).encode("utf-8"))
    return md5_hash.hexdigest(), timestr
