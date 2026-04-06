# -*- coding: utf-8 -*-
"""
JustPay API 客户端
Base URL: https://payment.winepipeline.com
app_code: screen_recorder
"""
import requests

BASE_URL = "https://payment.winepipeline.com"
APP_CODE = "screen_recorder"
TIMEOUT = 10


def fetch_plans() -> tuple:
    """
    获取方案列表
    返回 (plans_list, public_key)
    plans_list: [{id, name, price, duration_days, ...}, ...]
    """
    try:
        resp = requests.get(
            "{}/api/plans".format(BASE_URL),
            params={"app_code": APP_CODE},
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        # API returns {"success": true, "data": {"plans": [...], "public_key": "..."}}
        inner = data.get("data", data)
        plans = inner.get("plans", [])
        public_key = inner.get("public_key", "")
        return plans, public_key
    except Exception as e:
        print("[API] fetch_plans error: {}".format(e))
        return [], ""


def create_order(plan_id: int, machine_code: str) -> dict:
    """
    创建订单
    返回 {order_no, code_url, amount} 或空 dict
    """
    try:
        resp = requests.post(
            "{}/api/order/create".format(BASE_URL),
            json={
                "app_code": APP_CODE,
                "plan_id": plan_id,
                "machine_code": machine_code,
            },
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("success") and "data" in data:
            return data["data"]
        return data
    except Exception as e:
        print("[API] create_order error: {}".format(e))
        return {}


def check_order(order_no: str) -> dict:
    """
    查询订单状态
    返回 {status, license_code, expire_date}
    status: "pending" | "paid" | "expired"
    """
    try:
        resp = requests.get(
            "{}/api/order/check".format(BASE_URL),
            params={"order_no": order_no, "app_code": APP_CODE},
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("success") and "data" in data:
            return data["data"]
        return data
    except Exception as e:
        print("[API] check_order error: {}".format(e))
        return {"status": "error"}


def verify_license_online(license_code: str) -> dict:
    """
    在线验证许可证
    返回 {valid, message, ...}
    """
    try:
        resp = requests.post(
            "{}/api/license/verify".format(BASE_URL),
            json={
                "app_code": APP_CODE,
                "license_code": license_code,
            },
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print("[API] verify_license_online error: {}".format(e))
        return {"valid": False, "message": str(e)}
