# 简化版支付授权服务设计文档 v1.0

> **项目**: 录屏王 - 支付+注册码服务（简化版）
> **版本**: v1.0
> **日期**: 2026-04-04
> **升级目标**: 无缝衔接 `LICENSE_SYSTEM_DESIGN.md` v3.1 完整版

---

## 一、设计目标

### 1.1 本版本范围

一个**单文件、零数据库、硬编码配置**的最小可运行服务，仅覆盖：

1. 微信扫码支付（Native Pay）
2. 支付成功后自动生成 Ed25519 签名注册码
3. 客户端查询订单状态并获取注册码
4. 注册码格式与 v3.1 完全一致

### 1.2 不在本版本范围

| 功能 | 说明 |
|------|------|
| 管理后台 | v3.1 版本提供 |
| 多App支持 | 硬编码 `screen_recorder`，v3.1 通过 `app_code` 扩展 |
| 动态价格 | 硬编码在代码中，v3.1 从数据库读取 |
| 注册码生成器Web页面 | v3.1 的管理后台提供 |
| 离线注册码管理 | v3.1 提供完整管理 |

### 1.3 核心原则：API契约兼容

**简化版的每一个公开API，其请求格式和响应格式都与 v3.1 完全一致。**

升级路径：
```
简化版 (api_server/)  ──→  完整版 (subscription_server/)
     │                           │
     │  硬编码配置                │  数据库 + 管理后台
     │  单服务                    │  双服务 (公开API + 管理后台)
     │  SQLite文件               │  MySQL
     │                           │
     └─── 客户端代码无需任何改动 ───┘
```

客户端只关心公开API的请求/响应格式，不关心服务端实现。只要接口不变，后端从简化版切换到完整版是透明替换。

---

## 二、项目结构

```
api_server/
├── main.py              # 服务入口 + 所有路由（单文件）
├── config.py            # 硬编码配置（密钥、方案、微信配置）
├── crypto.py            # Ed25519签名/验签（直接内嵌，无外部依赖）
├── wechat_pay.py        # 微信支付V3 Native Pay封装
├── requirements.txt     # 依赖：flask, cryptography, requests
└── data/                # 运行时自动创建
    └── orders.db        # SQLite（仅存订单，无需手动建表）
```

对比 v3.1 的 15+ 文件 + MySQL + 双服务，简化版仅 **4个Python文件 + 1个依赖声明**。

---

## 三、硬编码配置

```python
# config.py

# ========== 应用配置（v3.1中从数据库apps表读取）==========
APP_CODE = "screen_recorder"
APP_NAME = "录屏王"

# ========== 授权方案（v3.1中从数据库license_plans表读取）==========
# 注意：id、plan_code、plan_name、price、duration_days 字段名与v3.1完全一致
PLANS = [
    {
        "id": 1,
        "plan_code": "single",
        "plan_name": "单日通行证",
        "price": 1.99,
        "duration_days": 1
    },
    {
        "id": 2,
        "plan_code": "monthly",
        "plan_name": "月度授权包",
        "price": 5.99,
        "duration_days": 30
    },
    {
        "id": 3,
        "plan_code": "yearly",
        "plan_name": "年度授权包",
        "price": 19.90,
        "duration_days": 365
    },
    {
        "id": 4,
        "plan_code": "permanent",
        "plan_name": "永久买断",
        "price": 39.90,
        "duration_days": 9999
    }
]

# ========== Ed25519密钥对（v3.1中从数据库system_config表读取）==========
# 部署时生成，私钥仅服务端使用，公钥硬编码到客户端
LICENSE_PRIVATE_KEY = ""  # Base64编码的Ed25519私钥
LICENSE_PUBLIC_KEY = ""   # Base64编码的Ed25519公钥（也要给客户端）

# ========== 微信支付配置（v3.1中从数据库system_config表读取）==========
WECHAT_APP_ID = ""        # 微信AppID（公众号/小程序）
WECHAT_MCH_ID = ""        # 微信商户号
WECHAT_API_KEY = ""       # 微信APIv3密钥
WECHAT_SERIAL_NO = ""     # 商户API证书序列号
WECHAT_PRIVATE_KEY = ""   # 商户API私钥（PEM格式，用于签名）
WECHAT_NOTIFY_URL = "https://recorder.winepipeline.com/pay/notify"

# ========== 服务配置 ==========
SERVICE_PORT = 8001
```

### 升级说明

从简化版升级到 v3.1 时：
- `PLANS` 列表 → 迁入 `license_plans` 数据库表
- `LICENSE_PRIVATE_KEY` → 迁入 `system_config` 表
- `WECHAT_*` → 迁入 `system_config` 表
- 客户端无需改动

---

## 四、注册码格式（与v3.1完全一致）

### 4.1 二进制结构

```
注册码二进制结构（78字节）

┌──────────┬──────────┬────────────────┬────────────┬──────────────┐
│ 偏移     │ 长度     │ 字段           │ 说明       │ 示例值       │
├──────────┼──────────┼────────────────┼────────────┼──────────────┤
│ 0        │ 1字节    │ version        │ 版本号     │ 0x03 (v3)    │
│ 1        │ 1字节    │ plan_id        │ 方案ID     │ 0x02         │
│ 2        │ 8字节    │ cpu_hash       │ CPU哈希    │ ABCD1234...  │
│ 10       │ 4字节    │ expire_ts      │ 到期时间戳  │ 大端序       │
│ 14       │ 64字节   │ signature      │ Ed25519签名 │ (二进制)     │
└──────────┴──────────┴────────────────┴────────────┴──────────────┘

最终格式: REC-{URL安全Base64编码的78字节}
```

### 4.2 签名/验签

签名逻辑与 v3.1 的 `shared/crypto/license_signer.py` 完全一致：

```python
# crypto.py（简化版，直接内嵌签名和验签）

import base64
import struct
from datetime import datetime, timedelta
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey, Ed25519PublicKey
)
from cryptography.hazmat.primitives import serialization
from cryptography.exceptions import InvalidSignature

VERSION = 3
DATA_LENGTH = 14
SIGNATURE_LENGTH = 64
TOTAL_LENGTH = 78


def generate_key_pair() -> tuple:
    """生成Ed25519密钥对，返回 (private_key_b64, public_key_b64)"""
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    priv_bytes = private_key.private_bytes(
        serialization.Encoding.Raw,
        serialization.PrivateFormat.Raw,
        serialization.NoEncryption()
    )
    pub_bytes = public_key.public_bytes(
        serialization.Encoding.Raw,
        serialization.PublicFormat.Raw
    )
    return (
        base64.b64encode(priv_bytes).decode(),
        base64.b64encode(pub_bytes).decode()
    )


def sign_license(machine_code: str, plan_id: int, duration_days: int,
                 private_key_b64: str) -> str:
    """生成注册码（与v3.1 LicenseSigner.sign 完全一致）"""
    private_bytes = base64.b64decode(private_key_b64)
    private_key = Ed25519PrivateKey.from_private_bytes(private_bytes)

    clean_code = machine_code.replace('-', '').upper()[:16].ljust(16, '0')
    cpu_hash_bytes = bytes.fromhex(clean_code)

    expire_ts = int((datetime.now() + timedelta(days=duration_days)).timestamp())

    data_to_sign = bytes([VERSION, plan_id]) + cpu_hash_bytes + struct.pack('>I', expire_ts)
    signature = private_key.sign(data_to_sign)
    full_data = data_to_sign + signature

    encoded = base64.b64encode(full_data).decode()
    encoded = encoded.replace('+', '-').replace('/', '_')
    return f"REC-{encoded}"


def verify_license(license_code: str, public_key_b64: str) -> dict:
    """验签注册码（与v3.1 LicenseVerifier.verify 完全一致）"""
    try:
        if not license_code.startswith("REC-"):
            return {"valid": False, "message": "注册码格式错误"}

        encoded = license_code[4:].replace('-', '+').replace('_', '/')
        padding = 4 - len(encoded) % 4
        if padding != 4:
            encoded += '=' * padding
        full_data = base64.b64decode(encoded)

        if len(full_data) != TOTAL_LENGTH:
            return {"valid": False, "message": f"注册码长度错误：{len(full_data)}"}

        version = full_data[0]
        plan_id = full_data[1]
        cpu_hash = full_data[2:10]
        expire_ts = struct.unpack('>I', full_data[10:14])[0]
        signature = full_data[14:78]

        if version != VERSION:
            return {"valid": False, "message": f"版本不支持：v{version}"}

        pub_bytes = base64.b64decode(public_key_b64)
        public_key = Ed25519PublicKey.from_public_bytes(pub_bytes)

        try:
            public_key.verify(signature, full_data[:14])
        except InvalidSignature:
            return {"valid": False, "message": "签名无效"}

        expire_date = datetime.fromtimestamp(expire_ts)
        days_left = (expire_date - datetime.now()).days

        if days_left <= 0:
            return {"valid": False, "message": "注册码已过期"}

        return {
            "valid": True,
            "plan_id": plan_id,
            "cpu_hash": cpu_hash.hex().upper(),
            "expire_date": expire_date.strftime("%Y-%m-%d"),
            "expire_ts": expire_ts,
            "days_left": days_left,
            "message": "验签成功"
        }
    except Exception as e:
        return {"valid": False, "message": f"解析错误：{str(e)}"}
```

---

## 五、API接口设计（与v3.1公开API完全一致）

### 5.1 获取授权方案

```
GET /api/plans?app_code=screen_recorder

响应（与v3.1完全一致）:
{
    "success": true,
    "data": {
        "plans": [
            {
                "id": 1,
                "plan_code": "single",
                "plan_name": "单日通行证",
                "price": 1.99,
                "duration_days": 1
            },
            ...
        ],
        "public_key": "MCowBQYDK2VwAyEA..."
    }
}
```

**简化版实现**：直接返回 `config.PLANS` 和 `config.LICENSE_PUBLIC_KEY`。
**v3.1实现**：从数据库查询 `license_plans` 表和 `system_config` 表。
**客户端视角**：完全相同。

### 5.2 创建订单

```
POST /api/order/create

请求（与v3.1完全一致）:
{
    "app_code": "screen_recorder",
    "plan_id": 2,
    "machine_code": "ABCD-1234-EFGH-5678"
}

响应（与v3.1完全一致）:
{
    "success": true,
    "data": {
        "order_no": "20250403123456",
        "code_url": "weixin://wxpay/...",
        "amount": 5.99
    }
}
```

**简化版实现**：
1. 从 `config.PLANS` 查找 `plan_id`
2. 调用微信 Native Pay API 生成支付二维码
3. 写入 SQLite `orders` 表
4. 返回 `order_no` + `code_url`

**v3.1实现**：写入 MySQL `orders` 表，其余逻辑相同。

### 5.3 查询订单

```
GET /api/order/check?order_no=20250403123456

响应（与v3.1完全一致）:
{
    "success": true,
    "data": {
        "paid": true,
        "license_code": "REC-...",
        "expire_date": "2025-05-03"
    }
}
```

**简化版实现**：查 SQLite `orders` 表，返回订单状态。
**v3.1实现**：查 MySQL `orders` 表，其余逻辑相同。

### 5.4 微信支付回调

```
POST /pay/notify

请求: 微信支付平台发送的回调通知（JSON格式，V3）

响应: HTTP 200 + {"code": "MESSAGE", "message": "成功"}
```

**处理流程**：
1. 验证微信签名
2. 解析 `out_trade_no`（订单号）和 `transaction_id`
3. 更新 SQLite 订单状态为 `paid`
4. 使用私钥签名生成注册码
5. 将注册码写入订单记录

### 5.5 接口兼容对照表

| API | 简化版 | v3.1 | 请求格式 | 响应格式 |
|-----|--------|------|----------|----------|
| `GET /api/plans` | 硬编码返回 | 数据库查询 | 一致 | 一致 |
| `POST /api/order/create` | SQLite写入 | MySQL写入 | 一致 | 一致 |
| `GET /api/order/check` | SQLite查询 | MySQL查询 | 一致 | 一致 |
| `POST /pay/notify` | SQLite更新 | MySQL更新 | 一致 | 一致 |

---

## 六、数据存储

### 6.1 SQLite 订单表

简化版使用 SQLite 单表，自动建表，无需手动初始化：

```sql
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_no TEXT UNIQUE NOT NULL,
    plan_id INTEGER NOT NULL,
    cpu_id TEXT,
    amount REAL NOT NULL,
    status TEXT DEFAULT 'pending',        -- pending / paid / closed
    wechat_transaction_id TEXT,
    license_code TEXT,
    expire_date TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    paid_at TIMESTAMP
);
```

### 6.2 升级迁移路径

升级到 v3.1 时：
```
SQLite orders 表  →  MySQL orders 表（结构兼容，字段名一致）
新增 MySQL表: apps, license_plans, licenses, admins, system_config
硬编码 PLANS    →  MySQL license_plans 表（字段名一致，INSERT即可）
硬编码 密钥     →  MySQL system_config 表
```

---

## 七、微信支付流程

### 7.1 整体流程

```
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│  客户端   │     │ api_server│     │  微信平台  │     │ Ed25519  │
└────┬─────┘     └────┬─────┘     └────┬─────┘     └────┬─────┘
     │                 │                 │                 │
     │ 1. POST /api/order/create        │                 │
     │  {plan_id, machine_code}         │                 │
     │────────────────→│                │                 │
     │                 │ 2. 调用Native   │                 │
     │                 │    Pay API      │                 │
     │                 │────────────────→│                 │
     │                 │ 3. 返回code_url │                 │
     │                 │←────────────────│                 │
     │ 4. 返回order_no + code_url       │                 │
     │←────────────────│                │                 │
     │                 │                │                 │
     │ 5. 展示二维码    │                │                 │
     │    用户扫码支付   │                │                 │
     │                 │                │                 │
     │                 │ 6. 支付回调通知  │                 │
     │                 │←────────────────│                 │
     │                 │ 7. 签名生成注册码│                 │
     │                 │─────────────────────────────────→│
     │                 │ 8. 签名结果      │                 │
     │                 │←─────────────────────────────────│
     │                 │ 9. 更新订单状态  │                 │
     │                 │    保存注册码    │                 │
     │                 │                │                 │
     │ 10. 轮询 GET /api/order/check    │                 │
     │────────────────→│                │                 │
     │ 11. 返回 paid=true + license_code │                 │
     │←────────────────│                │                 │
     │                 │                │                 │
     │ 12. 本地验签     │                │                 │
     │     激活成功     │                │                 │
     └─────────────────┘                │                 │
```

### 7.2 订单号生成规则

```python
import time
def generate_order_no():
    """年月日时分秒 + 4位随机数，共20位"""
    return time.strftime("%Y%m%d%H%M%S") + str(random.randint(1000, 9999))
```

---

## 八、客户端录制拦截与付费弹窗

### 8.1 录制按钮拦截逻辑

当前 `_toggle_record()` 直接调用 `_start_record()`。改动点：

```
用户点击录制按钮
    │
    ├─→ 检查本地 license.json
    │       │
    │       ├─ 已激活且未过期 → 直接开始录制（原有逻辑）
    │       │
    │       └─ 未激活或已过期 → 弹出付费弹窗
    │                            │
    │                            ├─ 支付/激活成功 → 开始录制
    │                            └─ 用户关闭弹窗 → 取消录制
    │
    └─→ 无网络时：仍可读取本地缓存离线验签
           ├─ 验签通过 → 正常录制
           └─ 验签失败 → 弹出付费弹窗（仅兑换码可用）
```

改动集中在 `ui/main_window.py` 的 `_toggle_record()` 方法，新增一个激活状态检查函数。

### 8.2 付费弹窗交互流程

```
┌──────────────────────────────────────────────────────────────┐
│                                                               │
│                    激活录屏王                                  │
│                                                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │
│  │  单日通行证   │  │  月度授权包   │  │  年度授权包   │  ...    │
│  │   ¥1.99     │  │   ¥5.99     │  │   ¥19.90    │          │
│  │   1天       │  │   30天      │  │   365天      │          │
│  └─────────────┘  └─────────────┘  └─────────────┘          │
│         ▲ 用户点击选择一个方案                                   │
│         │                                                     │
│  ┌─────────────────────────────────────────────────────┐    │
│  │                                                      │    │
│  │     ┌──────────────────┐                             │    │
│  │     │                  │                             │    │
│  │     │    微信支付二维码   │    ← 服务端返回 code_url    │    │
│  │     │                  │                             │    │
│  │     └──────────────────┘                             │    │
│  │                                                      │    │
│  │     请使用微信扫码支付 ¥5.99                           │    │
│  │     订单号: 202604041430221234                        │    │
│  │                                                      │    │
│  │     ● 等待支付中...  (每2秒轮询 /api/order/check)       │    │
│  │                                                      │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                               │
│  ─────────── 或 ────────────                                  │
│                                                               │
│  已有注册码？                                                  │
  │  机器码: ABCD-1234-EFGH-5678        [复制]                 │
│  注册码: [____________________]                              │
│                              [激活]                          │
│                                                               │
│                                        [×] 关闭              │
└──────────────────────────────────────────────────────────────┘
```

### 8.3 弹窗内状态流转

```
弹窗打开
    │
    ├─ Step 1: 调用 GET /api/plans 获取方案列表 + 公钥
    │          失败则使用硬编码公钥做离线验签后备
    │
    ├─ Step 2: 用户选择方案 → 点击"购买"
    │          │
    │          ├─ 调用 POST /api/order/create
    │          │   发送: { plan_id, machine_code }
    │          │
    │          ├─ 服务端返回 code_url
    │          │
    │          ├─ 客户端将 code_url 生成二维码展示
    │          │
    │          └─ 启动轮询定时器（QTimer, 每2秒）
    │              │
    │              ├─ GET /api/order/check?order_no=xxx
    │              │
    │              ├─ paid=false → 继续等待
    │              │
    │              └─ paid=true → 收到 license_code
    │                  │
    │                  ├─ 本地 Ed25519 验签
    │                  ├─ 验签通过 → 保存 license.json
    │                  ├─ 关闭弹窗
    │                  └─ 自动开始录制 ← 回到 _start_record()
    │
    ├─ Step 2（兑换码路径）: 用户粘贴注册码 → 点击"激活"
    │          │
    │          ├─ 本地 Ed25519 验签
    │          ├─ 验签通过 → 保存 license.json
    │          ├─ 关闭弹窗
    │          └─ 自动开始录制
    │
    └─ 用户关闭弹窗 → 取消，不录制
```

### 8.4 客户端新增模块

```
license/
├── __init__.py
├── activation.py    # 激活状态管理：check_activation(), activate_with_code()
├── cache_manager.py # 本地 license.json 读写
├── verifier.py      # Ed25519 验签（内嵌硬编码公钥）
└── machine_code.py  # 机器码生成（SHA256 of CPU ID）

ui/
├── pay_dialog.py    # 新增：付费弹窗（方案选择 + 二维码 + 兑换码）
└── main_window.py   # 修改：_toggle_record() 增加拦截逻辑
```

### 8.5 客户端改动点汇总

| 文件 | 改动 |
|------|------|
| `ui/main_window.py` | `_toggle_record()` 增加激活检查，未激活时弹出 `PayDialog` |
| `ui/pay_dialog.py` | **新增**：付费弹窗，含方案选择、二维码、兑换码三个区域 |
| `license/activation.py` | **新增**：启动时检查激活状态，激活/续费入口 |
| `license/cache_manager.py` | **新增**：读写 `%LOCALAPPDATA%/录屏王/license.json` |
| `license/verifier.py` | **新增**：Ed25519 离线验签，硬编码公钥 |
| `license/machine_code.py` | **新增**：获取机器码 |

---

## 九、启动与部署

### 9.1 初始化

```bash
# 1. 安装依赖
cd api_server
pip install -r requirements.txt

# 2. 生成密钥对（首次部署执行一次）
python -c "from crypto import generate_key_pair; priv, pub = generate_key_pair(); print(f'Private: {priv}\nPublic:  {pub}')"

# 3. 将生成的密钥填入 config.py
#    LICENSE_PRIVATE_KEY = "生成的私钥"
#    LICENSE_PUBLIC_KEY = "生成的公钥"
#    将公钥同时硬编码到客户端

# 4. 填入微信支付配置
#    WECHAT_APP_ID, WECHAT_MCH_ID, WECHAT_API_KEY 等

# 5. 启动服务
python main.py
```

### 9.2 requirements.txt

```
flask>=3.0
cryptography>=42.0
requests>=2.31
```

---

## 十、升级到v3.1完整版的检查清单

当需要从简化版升级到 v3.1 完整版时，按以下步骤操作：

### 10.1 数据迁移

```bash
# 1. 导出SQLite订单数据
sqlite3 data/orders.db "SELECT * FROM orders;" > orders_export.csv

# 2. 导入到MySQL（v3.1的orders表结构兼容）
mysqlimport --fields-terminated-by='|' license_system orders_export.csv
```

### 10.2 配置迁移

| 简化版 (config.py) | v3.1 (MySQL system_config表) |
|---------------------|------------------------------|
| `PLANS` 列表 | INSERT 到 `license_plans` 表 |
| `LICENSE_PRIVATE_KEY` | INSERT 到 `system_config` WHERE key='license_private_key' |
| `LICENSE_PUBLIC_KEY` | INSERT 到 `system_config` WHERE key='license_public_key' |
| `WECHAT_*` | INSERT 到 `system_config` 表 |

### 10.3 服务切换

```bash
# 1. 停止简化版服务
kill api_server/main.py

# 2. 启动v3.1服务
cd subscription_server/api_service && python main.py &
cd subscription_server/admin_service && python main.py &

# 3. Nginx反向代理指向新服务（端口可能变化）
```

### 10.4 客户端无需改动

客户端调用的4个API（`/api/plans`, `/api/order/create`, `/api/order/check`, `/pay/notify`）请求和响应格式完全一致，切换后端实现是透明操作。

---

## 十一、文件详细说明

### 11.1 main.py - 服务入口

单一Flask应用，包含所有路由。启动时自动初始化SQLite。

```
路由列表:
├── GET  /api/plans           # 获取授权方案
├── POST /api/order/create    # 创建订单
├── GET  /api/order/check     # 查询订单状态
└── POST /pay/notify          # 微信支付回调
```

### 11.2 config.py - 硬编码配置

所有配置项的说明见第三节。部署时需要填入：
- Ed25519 密钥对（crypto.py 生成）
- 微信支付商户配置

### 11.3 crypto.py - 签名/验签

Ed25519 签名和验签逻辑，与 v3.1 的 `license_signer.py` + `license_verifier.py` 完全等价。

### 11.4 wechat_pay.py - 微信支付

封装微信支付V3 Native Pay：
- `create_native_order()` - 创建Native支付订单，返回 `code_url`
- `verify_notification()` - 验证微信回调签名
- `parse_notification()` - 解密回调数据

---

**文档版本**: v1.0
**最后更新**: 2026-04-04
**升级目标**: `LICENSE_SYSTEM_DESIGN.md` v3.1
