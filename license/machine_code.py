# -*- coding: utf-8 -*-
"""
机器码生成 - 基于 CPU ID + 硬件信息
"""
import hashlib
import platform
import subprocess
import os


def get_machine_code() -> str:
    """返回 XXXX-XXXX-XXXX-XXXX 格式的机器码"""
    raw = _get_cpu_id()
    if not raw:
        raw = _get_fallback_id()
    h = hashlib.sha256(raw.encode()).hexdigest()[:16].upper()
    return "{}-{}-{}-{}".format(h[0:4], h[4:8], h[8:12], h[12:16])


def _get_cpu_id() -> str:
    """Windows: wmic cpu get ProcessorId"""
    try:
        result = subprocess.run(
            ['wmic', 'cpu', 'get', 'ProcessorId'],
            capture_output=True, text=True, timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        lines = [l.strip() for l in result.stdout.strip().split('\n') if l.strip()]
        if len(lines) >= 2:
            return lines[1]
    except Exception:
        pass
    return ""


def _get_fallback_id() -> str:
    """回退方案: hostname + 环境变量组合"""
    parts = [
        platform.node(),
        os.environ.get('USERNAME', ''),
        os.environ.get('COMPUTERNAME', ''),
        platform.processor(),
    ]
    return '|'.join(parts)
