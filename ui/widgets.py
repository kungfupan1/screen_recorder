# -*- coding: utf-8 -*-
"""
自定义控件 - 现代化UI组件 (DPI自适应 + 窗口缩放支持)
"""
from PySide6.QtWidgets import (
    QWidget, QPushButton, QLabel, QHBoxLayout, QFrame
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPainter, QColor, QBrush, QFont

from ui.styles import COLORS, BUTTON_STYLES, TIME_LABEL_STYLE, CARD_STYLE, TITLE_BAR_STYLE
from utils.config import sc, wsc


class ModernButton(QPushButton):
    """现代化按钮"""

    def __init__(self, text="", style_type="primary", parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        if style_type in BUTTON_STYLES:
            self.setStyleSheet(BUTTON_STYLES[style_type])


class RecordButton(QPushButton):
    """录制按钮 - 精美居中版本"""

    def __init__(self, zoom=1.0, parent=None):
        super().__init__(parent)
        self._zoom = zoom
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._is_recording = False
        btn = wsc(110, zoom)
        self.setFixedSize(btn, btn)
        self._apply_style()

    def _apply_style(self):
        z = self._zoom
        if self._is_recording:
            self.setText("■")
            half = wsc(55, z)
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 #e94560, stop:1 #c93050);
                    color: white;
                    border-radius: {half}px;
                    border: 4px solid rgba(233, 69, 96, 0.4);
                    font-size: {wsc(60, z)}px;
                    font-weight: bold;
                    padding: 0px;
                    padding-bottom: {wsc(20, z)}px;
                }}
                QPushButton:hover {{
                    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 #ff6b6b, stop:1 #e94560);
                }}
            """)
        else:
            self.setText("▶")
            half = wsc(55, z)
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 #e94560, stop:1 #ff6b6b);
                    color: white;
                    border-radius: {half}px;
                    border: none;
                    font-size: {wsc(66, z)}px;
                    font-weight: bold;
                    padding: 0px;
                    padding-left: {wsc(8, z)}px;
                    padding-bottom: {wsc(2, z)}px;
                }}
                QPushButton:hover {{
                    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 #ff6b6b, stop:1 #ff8585);
                }}
            """)

    def set_recording(self, is_recording: bool):
        self._is_recording = is_recording
        self._apply_style()

    def update_zoom(self, zoom):
        self._zoom = zoom
        btn = wsc(110, zoom)
        self.setFixedSize(btn, btn)
        self._apply_style()


class ModeButton(QPushButton):
    """模式选择按钮"""

    def __init__(self, text="", icon="", zoom=1.0, parent=None):
        super().__init__(f"{icon}  {text}" if icon else text, parent)
        self._zoom = zoom
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setCheckable(True)
        self.setFixedHeight(wsc(65, zoom))
        self._apply_style()

    def _apply_style(self):
        z = self._zoom
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['bg_card']};
                color: {COLORS['text_secondary']};
                border: 2px solid transparent;
                border-radius: {wsc(12, z)}px;
                padding: {wsc(12, z)}px {wsc(20, z)}px;
                font-size: {wsc(20, z)}px;
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
        """)

    def update_zoom(self, zoom):
        self._zoom = zoom
        self.setFixedHeight(wsc(65, zoom))
        self._apply_style()


class StatusIndicator(QWidget):
    """状态指示器"""

    def __init__(self, zoom=1.0, parent=None):
        super().__init__(parent)
        self._zoom = zoom
        self._status = "idle"
        dot = wsc(14, zoom)
        self.setFixedSize(dot, dot)

    def set_status(self, status: str):
        self._status = status
        self.update()

    def update_zoom(self, zoom):
        self._zoom = zoom
        dot = wsc(14, zoom)
        self.setFixedSize(dot, dot)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        color_map = {
            "recording": COLORS['accent'],
            "paused": COLORS['warning'],
            "idle": COLORS['success']
        }
        color = QColor(color_map.get(self._status, COLORS['text_secondary']))

        painter.setBrush(QBrush(color))
        painter.setPen(Qt.PenStyle.NoPen)
        dot = wsc(14, self._zoom)
        painter.drawEllipse(0, 0, dot, dot)


class TimeDisplay(QLabel):
    """时间显示组件"""

    def __init__(self, zoom=1.0, parent=None):
        super().__init__("00:00:00", parent)
        self._zoom = zoom
        self.setObjectName("timeLabel")
        self._apply_style()
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumHeight(wsc(50, zoom))

    def _apply_style(self):
        z = self._zoom
        self.setStyleSheet(f"""
            QLabel#timeLabel {{
                color: {COLORS['text_primary']};
                font-size: {wsc(36, z)}px;
                font-weight: bold;
                font-family: "Consolas", "Courier New", monospace;
                letter-spacing: {wsc(2, z)}px;
                background: transparent;
            }}
        """)

    def set_time(self, seconds: float):
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        self.setText(f"{hours:02d}:{minutes:02d}:{secs:02d}")

    def update_zoom(self, zoom):
        self._zoom = zoom
        self.setMinimumHeight(wsc(50, zoom))
        self._apply_style()


class CardWidget(QFrame):
    """卡片容器"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self.setStyleSheet(CARD_STYLE)


class TitleBar(QWidget):
    """自定义标题栏"""

    close_clicked = Signal()
    minimize_clicked = Signal()
    subscribe_clicked = Signal()  # 【新增】：暴露给主窗口的订阅点击信号

    def __init__(self, title="录屏王", zoom=1.0, parent=None):
        super().__init__(parent)
        self._zoom = zoom
        self.setObjectName("titleBar")
        z = zoom
        self.setFixedHeight(wsc(55, z))
        self._apply_style()

        layout = QHBoxLayout(self)
        layout.setContentsMargins(wsc(25, z), 0, wsc(15, z), 0)
        layout.setSpacing(0)

        # 标题文字
        self._title_label = QLabel(f"◉ {title}")
        self._title_label.setStyleSheet(f"""
            color: {COLORS['text_primary']};
            font-size: {wsc(28, z)}px;
            font-weight: bold;
            background: transparent;
        """)
        layout.addWidget(self._title_label)

        # 将左侧文字和右侧按钮推开的弹簧
        layout.addStretch()

        # 【新增】：订阅会员按钮 (放在最小化按钮前面)
        self._vip_btn = QPushButton("👑 订阅会员")
        self._vip_btn.setObjectName("vipBtn")
        self._vip_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._vip_btn.clicked.connect(self.subscribe_clicked)
        layout.addWidget(self._vip_btn)

        # 添加一点间距，不让它和最小化按钮太挤
        layout.addSpacing(wsc(10, z))

        # 最小化按钮
        self._min_btn = QPushButton("—")
        self._min_btn.setObjectName("minBtn")
        btn_sz = wsc(35, z)
        self._min_btn.setFixedSize(btn_sz, btn_sz)
        self._min_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._min_btn.clicked.connect(self.minimize_clicked)
        layout.addWidget(self._min_btn)

        # 关闭按钮
        self._close_btn = QPushButton("✕")
        self._close_btn.setObjectName("closeBtn")
        self._close_btn.setFixedSize(btn_sz, btn_sz)
        self._close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._close_btn.clicked.connect(self.close_clicked)
        layout.addWidget(self._close_btn)

        self._drag_pos = None

    def _apply_style(self):
        z = self._zoom
        self.setStyleSheet(f"""
            QWidget#titleBar {{
                background-color: {COLORS['bg_secondary']};
                border-top-left-radius: {wsc(15, z)}px;
                border-top-right-radius: {wsc(15, z)}px;
            }}

            /* 【新增】：订阅按钮的样式（无边框，悬停高亮） */
            QPushButton#vipBtn {{
                background-color: transparent;
                color: #ffc107; /* 使用显眼的金色 */
                border: none;
                font-size: {wsc(18, z)}px;
                font-weight: bold;
                padding: {wsc(5, z)}px {wsc(10, z)}px;
                border-radius: {wsc(8, z)}px;
            }}
            QPushButton#vipBtn:hover {{
                background-color: rgba(255, 193, 7, 0.15); /* 悬停时微微亮起金色底色 */
                color: #ffda6a;
            }}

            QPushButton#closeBtn {{
                background-color: transparent;
                color: {COLORS['text_secondary']};
                border: none;
                border-radius: {wsc(12, z)}px;
                padding: {wsc(5, z)}px;
                min-width: {wsc(30, z)}px;
                min-height: {wsc(30, z)}px;
            }}

            QPushButton#closeBtn:hover {{
                background-color: #e94560;
                color: white;
            }}

            QPushButton#minBtn {{
                background-color: transparent;
                color: {COLORS['text_secondary']};
                border: none;
                border-radius: {wsc(12, z)}px;
                padding: {wsc(5, z)}px;
                min-width: {wsc(30, z)}px;
                min-height: {wsc(30, z)}px;
            }}

            QPushButton#minBtn:hover {{
                background-color: {COLORS['success']};
                color: white;
            }}
        """)

    def update_zoom(self, zoom):
        self._zoom = zoom
        z = zoom
        self.setFixedHeight(wsc(55, z))
        self._apply_style()
        self.layout().setContentsMargins(wsc(25, z), 0, wsc(15, z), 0)
        self._title_label.setStyleSheet(f"""
            color: {COLORS['text_primary']};
            font-size: {wsc(28, z)}px;
            font-weight: bold;
            background: transparent;
        """)
        btn_sz = wsc(35, z)
        self._min_btn.setFixedSize(btn_sz, btn_sz)
        self._close_btn.setFixedSize(btn_sz, btn_sz)