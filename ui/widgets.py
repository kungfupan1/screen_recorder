# -*- coding: utf-8 -*-
"""
自定义控件 - 现代化UI组件 (DPI自适应 + 窗口缩放支持)
"""
from PySide6.QtWidgets import (
    QWidget, QPushButton, QLabel, QHBoxLayout, QVBoxLayout, QFrame, QDialog
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QPainter, QColor, QBrush, QFont, QLinearGradient

from qfluentwidgets import TransparentToolButton
from qfluentwidgets import FluentIcon as FIF

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


class DarkConfirmDialog(QDialog):
    """暗色主题确认弹窗 - 兑换码弹窗同款风格"""

    def __init__(self, title="确认", message="确定要执行此操作吗？", parent=None):
        super().__init__(parent)
        z = 1.0
        font_md = wsc(15, z)
        font_sm = wsc(13, z)

        self._result = False
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._drag_pos = None

        w, h = wsc(400, z), wsc(200, z)
        self.setFixedSize(w, h)

        # 背景框
        bg = QFrame(self)
        bg.setGeometry(0, 0, w, h)
        bg.setObjectName("ConfirmBg")
        bg.setStyleSheet(
            "QFrame#ConfirmBg { background-color: #1a1a2e; border-radius: 12px; border: 1px solid rgba(255, 255, 255, 0.08); }")
        outer = QVBoxLayout(bg)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # 标题栏: 左标题 + 右关闭按钮
        tb = QFrame()
        tb.setFixedHeight(wsc(40, z))
        tb.setStyleSheet("background: transparent;")
        tbl = QHBoxLayout(tb)
        tbl.setContentsMargins(wsc(16, z), 0, wsc(10, z), 0)
        tt = QLabel(title)
        tt.setStyleSheet("color: #ffffff; font-size: %dpx; font-weight: bold; background: transparent;" % font_md)
        tbl.addWidget(tt)
        tbl.addStretch()
        cb = TransparentToolButton(FIF.CLOSE, self)
        cb.setFixedSize(wsc(34, z), wsc(34, z))
        cb.clicked.connect(self._on_cancel)
        tbl.addWidget(cb)
        outer.addWidget(tb)

        # 正文
        body = QWidget()
        body.setStyleSheet("background: transparent;")
        bl = QVBoxLayout(body)
        bl.setContentsMargins(wsc(24, z), wsc(8, z), wsc(24, z), wsc(20, z))
        bl.setSpacing(wsc(20, z))

        msg_label = QLabel(message)
        msg_label.setWordWrap(True)
        msg_label.setStyleSheet("color: #a0a0a0; font-size: %dpx; background: transparent;" % font_sm)
        bl.addWidget(msg_label)

        bl.addStretch()

        # 按钮行
        btn_row = QHBoxLayout()
        btn_row.setSpacing(wsc(12, z))

        cancel_btn = QPushButton("取消")
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.setFixedSize(wsc(90, z), wsc(36, z))
        cancel_btn.setStyleSheet(
            "QPushButton { background-color: rgba(255,255,255,0.05); color: #aaaaaa; border: 1px solid rgba(255,255,255,0.1); border-radius: 6px; font-size: %dpx; } QPushButton:hover { background-color: rgba(255,255,255,0.1); color: #ffffff; }" % font_sm)
        cancel_btn.clicked.connect(self._on_cancel)
        btn_row.addWidget(cancel_btn)
        btn_row.addStretch()

        confirm_btn = QPushButton("确定退出")
        confirm_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        confirm_btn.setFixedSize(wsc(100, z), wsc(36, z))
        confirm_btn.setStyleSheet(
            "QPushButton { background-color: #e94560; color: #ffffff; border: none; border-radius: 6px; font-weight: bold; font-size: %dpx; } QPushButton:hover { background-color: #ff6b6b; }" % font_sm)
        confirm_btn.clicked.connect(self._on_confirm)
        btn_row.addWidget(confirm_btn)
        bl.addLayout(btn_row)

        outer.addWidget(body)

        # 居中于父窗口
        if parent:
            pg = parent.geometry()
            self.move(pg.x() + (pg.width() - w) // 2, pg.y() + (pg.height() - h) // 2)

    def _on_confirm(self):
        self._result = True
        self.accept()

    def _on_cancel(self):
        self._result = False
        self.reject()

    def result_yes(self):
        return self._result

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = e.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, e):
        if self._drag_pos and e.buttons() & Qt.MouseButton.LeftButton:
            self.move(e.globalPosition().toPoint() - self._drag_pos)


class AudioWaveWidget(QWidget):
    """录音状态下的音频波形动画 - 千千静听式频谱"""

    def __init__(self, zoom=1.0, parent=None):
        super().__init__(parent)
        self._zoom = zoom
        self.setFixedHeight(wsc(40, zoom))
        self._bars = 24
        self._heights = [0.0] * self._bars
        self._phase = 0.0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._animate)

    def start(self):
        self._timer.start(60)

    def stop(self):
        self._timer.stop()
        self._heights = [0.0] * self._bars
        self._phase = 0.0
        self.update()

    def _animate(self):
        import random
        import math
        self._phase += 0.15
        n = self._bars
        mid = n / 2.0
        for i in range(n):
            # 中间高两边低的钟形曲线
            bell = 1.0 - ((i - mid) / mid) ** 2
            bell = max(0.0, bell)
            # 用 phase 驱动正弦波，产生真正的流动跳动
            w1 = math.sin(self._phase + i * 0.6) * 0.5
            w2 = math.sin(self._phase * 1.8 + i * 0.35) * 0.3
            w3 = math.sin(self._phase * 0.7 + i * 1.2) * 0.2
            val = bell * (0.2 + 0.8 * (0.5 + 0.5 * (w1 + w2 + w3)))
            val += random.uniform(-0.06, 0.06)
            val = max(0.05, min(1.0, val))
            # 平滑插值
            self._heights[i] += (val - self._heights[i]) * 0.4
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w = self.width()
        h = self.height()
        z = self._zoom

        bar_w = max(2, wsc(3, z))
        gap = max(1, wsc(2, z))
        total_w = self._bars * bar_w + (self._bars - 1) * gap
        start_x = (w - total_w) / 2
        max_h = h - wsc(4, z)
        center_y = h / 2.0

        for i in range(self._bars):
            x = start_x + i * (bar_w + gap)
            bh = max(2, int(max_h * self._heights[i]))
            y = center_y - bh / 2.0

            grad = QLinearGradient(x, y, x, y + bh)
            grad.setColorAt(0, QColor(255, 255, 255, 200))
            grad.setColorAt(0.5, QColor(0, 217, 255, 220))
            grad.setColorAt(1, QColor(255, 255, 255, 200))
            painter.setBrush(QBrush(grad))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(int(x), int(y), bar_w, bh, 1, 1)

    def update_zoom(self, zoom):
        self._zoom = zoom
        self.setFixedHeight(wsc(40, zoom))
        self.setFixedHeight(wsc(40, zoom))


class AudioToggleButton(QPushButton):
    """音频开关 - 轻量图标标签，点击切换开/关"""

    # 🔊 的关闭态用 🔇，🎤 的关闭态图标不变（只靠颜色区分）
    _MUTE_ICON = {"🎤": "❌", "🔊": "🔇"}

    def __init__(self, icon_emoji="🎤", label_text="麦克风", zoom=1.0, parent=None):
        self._icon_emoji = icon_emoji
        self._label_text = label_text
        self._zoom = zoom
        self._off_icon = self._MUTE_ICON.get(icon_emoji, icon_emoji)
        super().__init__(f"{icon_emoji}  {label_text}", parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setCheckable(True)
        self.setFlat(True)
        self._apply_style()

    def _apply_style(self):
        z = self._zoom
        self.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: #666666;
                border: none;
                font-size: {wsc(20, z)}px;
                font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
                padding: 0px;
            }}
            QPushButton:hover {{
                color: #999999;
            }}
            QPushButton:checked {{
                color: #ffffff;
            }}
            QPushButton:checked:hover {{
                color: #dddddd;
            }}
        """)

    def _update_text(self):
        icon = self._icon_emoji if self.isChecked() else self._off_icon
        self.setText(f"{icon}  {self._label_text}")

    def nextCheckState(self):
        """重写以同步图标"""
        super().nextCheckState()
        self._update_text()

    def setChecked(self, checked):
        super().setChecked(checked)
        self._update_text()

    def update_zoom(self, zoom):
        self._zoom = zoom
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