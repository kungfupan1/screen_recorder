# -*- coding: utf-8 -*-
"""
许可证激活入口 - 启动检查 + 离线验签
"""
from datetime import datetime

from license.machine_code import get_machine_code
from license.verifier import verify
from license.cache_manager import load_license, save_license

# Ed25519 公钥 (Base64URL, 由服务端生成时对应)
PUBLIC_KEY_B64 = "foZSPWTO5g7FZgOAFjwewNcytCxe34mwu/UxP+c+sPM="

# 方案ID到名称的映射
PLAN_NAMES = {
    1: "月度",
    2: "季度",
    3: "年度",
    4: "终身",
}


def check_activation() -> dict:
    """
    启动时调用，检查本地许可证是否有效
    返回 {activated, plan_name, expire_date, days_left}
    """
    license_data = load_license()
    if not license_data or "license_code" not in license_data:
        return {"activated": False}

    # 检查机器码匹配
    current_machine = get_machine_code()
    saved_machine = license_data.get("machine_code", "")
    if current_machine != saved_machine:
        return {"activated": False}

    # 离线验签
    result = verify(license_data["license_code"], PUBLIC_KEY_B64)
    if not result.get("valid"):
        return {"activated": False}

    plan_id = result.get("plan_id", 0)
    plan_name = license_data.get("plan_name") or PLAN_NAMES.get(plan_id, "未知")

    return {
        "activated": True,
        "plan_name": plan_name,
        "expire_date": result.get("expire_date", ""),
        "days_left": result.get("days_left", 0),
    }


def activate_with_code(license_code: str, plan_name: str = "") -> dict:
    """
    用许可证码激活
    返回 {success, message, plan_name, expire_date}
    """
    result = verify(license_code, PUBLIC_KEY_B64)
    if not result.get("valid"):
        return {"success": False, "message": result.get("message", "验证失败")}

    plan_id = result.get("plan_id", 0)
    if not plan_name:
        plan_name = PLAN_NAMES.get(plan_id, "未知")

    machine_code = get_machine_code()

    # 保存到本地
    save_license({
        "license_code": license_code,
        "machine_code": machine_code,
        "plan_name": plan_name,
        "expire_date": result.get("expire_date", ""),
        "activated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })

    return {
        "success": True,
        "message": "激活成功",
        "plan_name": plan_name,
        "expire_date": result.get("expire_date", ""),
    }
