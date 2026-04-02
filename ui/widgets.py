"""
自定义控件 - 现代化UI组件
"""
from PySide6.QtWidgets import (
    QWidget, QPushButton, QLabel, QHBoxLayout, QFrame
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPainter, QColor, QBrush, QFont
from ui.styles import COLORS, BUTTON_STYLES, TIME_LABEL_STYLE, CARD_STYLE, TITLE_BAR_STYLE


class ModernButton(QPushButton):
    """现代化按钮"""

    def __init__(self, text="", style_type="primary", parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        if style_type in BUTTON_STYLES:
            self.setStyleSheet(BUTTON_STYLES[style_type])


class RecordButton(QPushButton):
    """录制按钮 - 精美居中版本"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._is_recording = False
        self.setFixedSize(110, 110)  # 稍微大一点
        self._apply_style()

    def _apply_style(self):
        if self._is_recording:
            # 录制中显示停止符号 ■ - 居中对齐
            self.setText("■")
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 #e94560, stop:1 #c93050);
                    color: white;
                    border-radius: 55px;
                    border: 4px solid rgba(233, 69, 96, 0.4);
                    font-size: 60px;
                    font-weight: bold;
                    padding: 0px;
                    padding-bottom: 20px;
                }}
                QPushButton:hover {{
                    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 #ff6b6b, stop:1 #e94560);
                }}
            """)
        else:
            # 就绪状态显示播放符号 ▶ - 居中对齐
            self.setText("▶")
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 #e94560, stop:1 #ff6b6b);
                    color: white;
                    border-radius: 55px;
                    border: none;
                    font-size: 66px;
                    font-weight: bold;
                    padding: 0px;
                    padding-left: 8px;
                    padding-bottom: 2px;
                }}
                QPushButton:hover {{
                    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 #ff6b6b, stop:1 #ff8585);
                }}
            """)

    def set_recording(self, is_recording: bool):
        self._is_recording = is_recording
        self._apply_style()


class ModeButton(QPushButton):
    """模式选择按钮"""

    def __init__(self, text="", icon="", parent=None):
        super().__init__(f"{icon}  {text}" if icon else text, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setCheckable(True)
        self.setFixedHeight(65)  # 增高以适应更大的字体
        self.setStyleSheet(BUTTON_STYLES['mode'])


class StatusIndicator(QWidget):
    """状态指示器"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._status = "idle"
        self.setFixedSize(14, 14)  # 稍大一点

    def set_status(self, status: str):
        self._status = status
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
        painter.drawEllipse(0, 0, 14, 14)


class TimeDisplay(QLabel):
    """时间显示组件"""

    def __init__(self, parent=None):
        super().__init__("00:00:00", parent)
        self.setObjectName("timeLabel")
        self.setStyleSheet(TIME_LABEL_STYLE)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumHeight(50)

    def set_time(self, seconds: float):
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        self.setText(f"{hours:02d}:{minutes:02d}:{secs:02d}")


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

    def __init__(self, title="录屏王", parent=None):  # 默认改为"录屏王"
        super().__init__(parent)
        self.setObjectName("titleBar")
        self.setFixedHeight(55)  # 增高一点
        self.setStyleSheet(TITLE_BAR_STYLE)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(25, 0, 15, 0)
        layout.setSpacing(0)

        # 标题文字
        title_label = QLabel(f"◉ {title}")
        title_label.setStyleSheet(f"""
            color: {COLORS['text_primary']};
            font-size: 28px;
            font-weight: bold;
            background: transparent;
        """)
        layout.addWidget(title_label)
        layout.addStretch()

        # 最小化按钮
        min_btn = QPushButton("—")
        min_btn.setObjectName("minBtn")
        min_btn.setFixedSize(35, 35)
        min_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        min_btn.clicked.connect(self.minimize_clicked)
        layout.addWidget(min_btn)

        # 关闭按钮
        close_btn = QPushButton("✕")
        close_btn.setObjectName("closeBtn")
        close_btn.setFixedSize(35, 35)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(self.close_clicked)
        layout.addWidget(close_btn)