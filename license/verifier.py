# -*- coding: utf-8 -*-
"""
许可证离线验签 - Ed25519
格式: REC-{Base64URL(78字节)}
  version(1) + plan_id(1) + machine_hash(8) + expire_ts(4, BE) + ed25519_sig(64)
"""
import base64
import struct
import time
from datetime import datetime

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey


def verify(license_code: str, public_key_b64: str) -> dict:
    """
    验证许可证码，返回 {valid, plan_id, expire_date, days_left, message}
    """
    try:
        # 去除 REC- 前缀
        if not license_code.startswith("REC-"):
            return {"valid": False, "message": "无效的许可证格式"}
        b64_part = license_code[4:]

        # Base64URL 解码
        padded = b64_part + "=" * (4 - len(b64_part) % 4)
        raw = base64.urlsafe_b64decode(padded)

        if len(raw) != 78:
            return {"valid": False, "message": "许可证数据长度错误"}

        version = raw[0]
        plan_id = raw[1]
        machine_hash = raw[2:10]
        expire_ts = struct.unpack(">I", raw[10:14])[0]
        signature = raw[14:78]

        # 验签
        pub_key_bytes = base64.urlsafe_b64decode(public_key_b64 + "=" * (4 - len(public_key_b64) % 4))
        pub_key = Ed25519PublicKey.from_public_bytes(pub_key_bytes)

        message = raw[:14]  # version + plan_id + machine_hash + expire_ts
        pub_key.verify(signature, message)

        # 检查过期
        expire_dt = datetime.utcfromtimestamp(expire_ts)
        now = datetime.utcnow()
        days_left = (expire_dt - now).days

        if days_left < 0:
            return {
                "valid": False,
                "plan_id": plan_id,
                "expire_date": expire_dt.strftime("%Y-%m-%d"),
                "days_left": days_left,
                "message": "许可证已过期"
            }

        return {
            "valid": True,
            "plan_id": plan_id,
            "expire_date": expire_dt.strftime("%Y-%m-%d"),
            "days_left": days_left,
            "message": "验证成功"
        }

    except InvalidSignature:
        return {"valid": False, "message": "签名验证失败"}
    except Exception as e:
        return {"valid": False, "message": "验证异常: {}".format(str(e))}
