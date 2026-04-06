# -*- coding: utf-8 -*-
"""
许可证本地缓存管理
存储路径: %LOCALAPPDATA%\录屏王\
"""
import os
import json


def _get_storage_dir() -> str:
    """获取存储目录"""
    base = os.environ.get('LOCALAPPDATA', os.path.expanduser('~'))
    d = os.path.join(base, '录屏王')
    if not os.path.exists(d):
        os.makedirs(d, exist_ok=True)
    return d


def _license_path() -> str:
    return os.path.join(_get_storage_dir(), 'license.json')


def _plans_cache_path() -> str:
    return os.path.join(_get_storage_dir(), 'plans_cache.json')


def save_license(data: dict):
    """保存许可证信息"""
    with open(_license_path(), 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_license() -> dict:
    """加载许可证信息，无则返回空 dict"""
    path = _license_path()
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def clear_license():
    """清除许可证"""
    path = _license_path()
    if os.path.exists(path):
        os.remove(path)


def save_plans_cache(plans: list, public_key: str):
    """缓存方案列表"""
    data = {"plans": plans, "public_key": public_key}
    with open(_plans_cache_path(), 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_plans_cache() -> tuple:
    """加载缓存的方案列表，返回 (plans, public_key)"""
    path = _plans_cache_path()
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data.get("plans", []), data.get("public_key", "")
        except Exception:
            pass
    return [], ""
