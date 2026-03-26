"""
现代化样式定义 - 精美的暗色主题
"""

# 颜色方案
COLORS = {
    'bg_primary': '#1a1a2e',      # 主背景色 - 深紫黑
    'bg_secondary': '#16213e',     # 次背景色
    'bg_card': '#0f3460',         # 卡片背景
    'accent': '#e94560',          # 强调色 - 珊瑚红
    'accent_hover': '#ff6b6b',    # 强调色悬停
    'text_primary': '#ffffff',    # 主文字
    'text_secondary': '#a0a0a0', # 次要文字
    'success': '#00d9ff',         # 成功/录制中 - 青色
    'warning': '#ffc107',         # 警告 - 黄色
    'border': '#2a2a4a',          # 边框
    'shadow': 'rgba(0, 0, 0, 0.3)', # 阴影
}

# 主窗口样式
MAIN_WINDOW_STYLE = f"""
QWidget {{
    font-family: "Microsoft YaHei", "Segoe UI", Arial, sans-serif;
    font-size: 14px;
}}

/* 主窗口 */
QMainWindow {{
    background-color: {COLORS['bg_primary']};
}}

/* 中央控件 */
QCentralWidget {{
    background-color: {COLORS['bg_primary']};
}}

/* 标签 */
QLabel {{
    color: {COLORS['text_primary']};
    background-color: transparent;
}}

/* 按钮基础样式 */
QPushButton {{
    border: none;
    border-radius: 8px;
    padding: 12px 24px;
    font-size: 14px;
    font-weight: bold;
}}

QPushButton:disabled {{
    background-color: #3a3a5a;
    color: #6a6a8a;
}}
"""

# 现代化按钮样式
BUTTON_STYLES = {
    'primary': f"""
        QPushButton {{
            background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 #e94560, stop:1 #ff6b6b);
            color: white;
            border-radius: 10px;
            padding: 15px 30px;
            font-size: 15px;
            font-weight: bold;
        }}
        QPushButton:hover {{
            background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 #ff6b6b, stop:1 #ff8585);
        }}
        QPushButton:pressed {{
            background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 #d63050, stop:1 #e94560);
        }}
        QPushButton:disabled {{
            background-color: #3a3a5a;
            color: #6a6a8a;
        }}
    """,

    'secondary': f"""
        QPushButton {{
            background-color: {COLORS['bg_card']};
            color: {COLORS['text_primary']};
            border: 2px solid {COLORS['border']};
            border-radius: 10px;
            padding: 15px 30px;
            font-size: 15px;
            font-weight: bold;
        }}
        QPushButton:hover {{
            background-color: #1a4a80;
            border-color: {COLORS['success']};
        }}
        QPushButton:pressed {{
            background-color: #0a2a50;
        }}
        QPushButton:disabled {{
            background-color: #2a2a4a;
            color: #5a5a7a;
        }}
    """,

    'record': f"""
        QPushButton {{
            background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 #e94560, stop:1 #c93050);
            color: white;
            border-radius: 50%;
            padding: 0px;
            min-width: 80px;
            max-width: 80px;
            min-height: 80px;
            max-height: 80px;
            font-size: 28px;
        }}
        QPushButton:hover {{
            background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 #ff6b6b, stop:1 #e94560);
        }}
        QPushButton:pressed {{
            background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 #d63050, stop:1 #b02040);
        }}
    """,

    'stop': f"""
        QPushButton {{
            background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 #00d9ff, stop:1 #0099cc);
            color: white;
            border-radius: 50%;
            padding: 0px;
            min-width: 80px;
            max-width: 80px;
            min-height: 80px;
            max-height: 80px;
            font-size: 24px;
        }}
        QPushButton:hover {{
            background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 #33e5ff, stop:1 #00b3e6);
        }}
        QPushButton:pressed {{
            background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 #00b3e6, stop:1 #0077aa);
        }}
    """,

    'mode': f"""
        QPushButton {{
            background-color: {COLORS['bg_card']};
            color: {COLORS['text_secondary']};
            border: 2px solid transparent;
            border-radius: 12px;
            padding: 12px 20px;
            font-size: 20px;
        }}
        QPushButton:hover {{
            background-color: #1a4a80;
            color: {COLORS['text_primary']};
        }}
        QPushButton:checked {{
            background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 {COLORS['bg_card']}, stop:1 #1a4a80);
            color: {COLORS['success']};
            border-color: {COLORS['success']};
        }}
    """,
}

# 卡片样式
CARD_STYLE = f"""
    QWidget#card {{
        background-color: {COLORS['bg_secondary']};
        border-radius: 20px;
        border: 1px solid {COLORS['border']};
    }}
"""

# 标题栏样式
TITLE_BAR_STYLE = f"""
    QWidget#titleBar {{
        background-color: {COLORS['bg_secondary']};
        border-top-left-radius: 15px;
        border-top-right-radius: 15px;
    }}

    QPushButton#closeBtn {{
        background-color: transparent;
        color: {COLORS['text_secondary']};
        border: none;
        border-radius: 12px;
        padding: 5px;
        min-width: 30px;
        min-height: 30px;
    }}

    QPushButton#closeBtn:hover {{
        background-color: #e94560;
        color: white;
    }}

    QPushButton#minBtn {{
        background-color: transparent;
        color: {COLORS['text_secondary']};
        border: none;
        border-radius: 12px;
        padding: 5px;
        min-width: 30px;
        min-height: 30px;
    }}

    QPushButton#minBtn:hover {{
        background-color: {COLORS['success']};
        color: white;
    }}
"""

# 状态标签样式
STATUS_LABEL_STYLE = f"""
    QLabel#statusLabel {{
        color: {COLORS['success']};
        font-size: 14px;
        font-weight: bold;
        padding: 5px 15px;
        background-color: rgba(0, 217, 255, 0.1);
        border-radius: 15px;
    }}
"""

# 时间显示样式
TIME_LABEL_STYLE = f"""
    QLabel#timeLabel {{
        color: {COLORS['text_primary']};
        font-size: 36px;
        font-weight: bold;
        font-family: "Consolas", "Courier New", monospace;
        letter-spacing: 2px;
    }}
"""