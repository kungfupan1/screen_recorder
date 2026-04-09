# -*- coding: utf-8 -*-
"""
主窗口 - 玻璃质感UI + 系统级等比缩放 (nativeEvent)
"""
import os
import shutil
import random
import ctypes
import tempfile
from ctypes import wintypes

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QScrollArea, QFileDialog, QCheckBox, QMessageBox, QMenu
)
from PySide6.QtCore import Qt, QTimer, QPoint, QPointF, QRect, Signal
from PySide6.QtGui import QPixmap, QImage, QColor, QPainter, QRadialGradient, QPen, QBrush

import cv2

from ui.widgets import RecordButton, ModeButton, StatusIndicator, TimeDisplay, TitleBar
from ui.styles import COLORS, BUTTON_STYLES
from recorder.controller import RecordController
from recorder.area_selector import select_area
from license.activation import check_activation
from utils.config import sc, wsc

# 设计稿基准尺寸
_BASE_W = 670
_BASE_H = 1260

# Windows 消息常量
WM_NCHITTEST = 0x0084
WM_SIZING = 0x0214
WM_GETMINMAXINFO = 0x0024

HTCLIENT = 1
HTCAPTION = 2
HTLEFT = 10
HTRIGHT = 11
HTTOP = 12
HTTOPLEFT = 13
HTTOPRIGHT = 14
HTBOTTOM = 15
HTBOTTOMLEFT = 16
HTBOTTOMRIGHT = 17

WMSZ_LEFT = 1
WMSZ_RIGHT = 2
WMSZ_TOP = 3
WMSZ_TOPLEFT = 4
WMSZ_TOPRIGHT = 5
WMSZ_BOTTOM = 6
WMSZ_BOTTOMLEFT = 7
WMSZ_BOTTOMRIGHT = 8

_BORDER = 8


# ────────────────── 勾选框样式工具 ──────────────────
def _gen_cb_images(sz):
    """生成带 ✓ 打勾图标和空白图标的 PNG，返回 (checked_url, unchecked_url)"""
    r = max(1, int(sz * 0.28))

    # --- Checked: 青色底 + 白色 ✓ ---
    pm = QPixmap(sz, sz)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setBrush(QBrush(QColor("#00d9ff")))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawRoundedRect(0, 0, sz, sz, r, r)
    lw = max(2.0, sz / 10.0)
    pen = QPen(QColor("#ffffff"), lw)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    p.drawLine(QPointF(sz * 0.22, sz * 0.50), QPointF(sz * 0.40, sz * 0.68))
    p.drawLine(QPointF(sz * 0.40, sz * 0.68), QPointF(sz * 0.78, sz * 0.30))
    p.end()
    path_on = os.path.join(tempfile.gettempdir(), f"_cb_on_{sz}.png").replace("\\", "/")
    pm.save(path_on, "PNG")

    # --- Unchecked: 暗灰底 + 浅灰边 ---
    pm2 = QPixmap(sz, sz)
    pm2.fill(Qt.GlobalColor.transparent)
    p2 = QPainter(pm2)
    p2.setRenderHint(QPainter.RenderHint.Antialiasing)
    p2.setPen(QPen(QColor(255, 255, 255, 60), 1))
    p2.setBrush(QColor(255, 255, 255, 15))
    p2.drawRoundedRect(0, 0, sz, sz, r, r)
    p2.end()
    path_off = os.path.join(tempfile.gettempdir(), f"_cb_off_{sz}.png").replace("\\", "/")
    pm2.save(path_off, "PNG")

    return path_on, path_off


def _cb_style(z, font_sz=22, ind_sz=32, spacing=12):
    """生成带 ✓ 打勾图标的 QCheckBox 样式表"""
    sz = wsc(ind_sz, z)
    on_url, off_url = _gen_cb_images(sz)
    return (
        "QCheckBox { color: #888888; font-size: %dpx; spacing: %dpx; background: transparent; }"
        "QCheckBox:checked { color: #ffffff; }"
        "QCheckBox::indicator { width: %dpx; height: %dpx; image: url(%s); }"
        "QCheckBox::indicator:checked { image: url(%s); }"
    ) % (wsc(font_sz, z), wsc(spacing, z), sz, sz, off_url, on_url)


class MINMAXINFO(ctypes.Structure):
    _fields_ = [
        ("ptReserved", wintypes.POINT),
        ("ptMaxSize", wintypes.POINT),
        ("ptMaxPosition", wintypes.POINT),
        ("ptMinTrackSize", wintypes.POINT),
        ("ptMaxTrackSize", wintypes.POINT),
    ]


# ────────────────── 动态失焦光斑背景底层 (自适应缩放版) ──────────────────
class BokehBackground(QWidget):
    """纯代码渲染的动态失焦光斑背景"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(
            "background-color: #1a1a2e; border-radius: 16px; border: 1px solid rgba(255, 255, 255, 0.05);")

        self._particles = []
        self._num_particles = 3
        self._colors = [
            QColor(0, 217, 255, 40),
            QColor(138, 43, 226, 30),
            QColor(255, 255, 255, 20),
            QColor(100, 149, 237, 35)
        ]

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_particles)
        self._timer.start(33)
        self._initialized = False

    def _init_particles(self):
        w, h = self.width(), self.height()
        if w == 0 or h == 0: return
        self._particles.clear()
        for _ in range(self._num_particles):
            # 【核心魔法】：不再记录绝对像素，而是记录比例 (0.0 ~ 1.0)
            nx, ny = random.random(), random.random()
            # 移动速度也是比例
            nvx, nvy = random.uniform(-0.001, 0.001), random.uniform(-0.001, 0.001)
            # 半径占窗口宽度的比例 (大约 12% 到 30%)
            r_ratio = random.uniform(0.12, 0.30)

            color = random.choice(self._colors)
            self._particles.append({'nx': nx, 'ny': ny, 'nvx': nvx, 'nvy': nvy, 'r_ratio': r_ratio, 'color': color})
        self._initialized = True

    def _update_particles(self):
        if not self._initialized: return
        for p in self._particles:
            p['nx'] += p['nvx']
            p['ny'] += p['nvy']
            # 碰撞反弹 (基于百分比边界检测)
            if p['nx'] > 1.2 or p['nx'] < -0.2: p['nvx'] *= -1
            if p['ny'] > 1.2 or p['ny'] < -0.2: p['nvy'] *= -1
        self.update()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if not self._initialized:
            self._init_particles()

    def paintEvent(self, event):
        super().paintEvent(event)
        if not self._initialized: return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)

        w, h = self.width(), self.height()

        for p in self._particles:
            # 【核心魔法】：每次绘制时，用最新的窗口宽高乘以比例，实时算出当前尺寸！
            x = p['nx'] * w
            y = p['ny'] * h
            radius = p['r_ratio'] * w

            gradient = QRadialGradient(x, y, radius)
            center_color = p['color']
            edge_color = QColor(center_color)
            edge_color.setAlpha(0)
            gradient.setColorAt(0, center_color)
            gradient.setColorAt(0.7, center_color)
            gradient.setColorAt(1, edge_color)
            painter.setBrush(gradient)
            painter.drawEllipse(int(x - radius), int(y - radius), int(radius * 2), int(radius * 2))
# ────────────────── 视频卡片 ──────────────────
class VideoCard(QFrame):
    """视频卡片"""

    def __init__(self, video_path, zoom=1.0, parent=None):
        super().__init__(parent)
        self.video_path = video_path
        self._zoom = zoom
        self.setObjectName("videoCard")
        self._apply_size()
        self.setStyleSheet("""
            #videoCard { background-color: rgba(255, 255, 255, 0.04); border-radius: 12px; border: 1px solid rgba(255, 255, 255, 0.06); }
            #videoCard:hover { border-color: #00d9ff; background-color: rgba(0, 217, 255, 0.05); }
        """)

        layout = QVBoxLayout(self)
        self._layout = layout
        layout.setContentsMargins(wsc(10, zoom), wsc(10, zoom), wsc(10, zoom), wsc(10, zoom))
        layout.setSpacing(wsc(6, zoom))

        self.thumb = QLabel()
        self.thumb.setFixedSize(wsc(140, zoom), wsc(75, zoom))
        self.thumb.setStyleSheet("background-color: rgba(0, 0, 0, 0.3); border-radius: 6px;")
        self.thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumb.setText("📹")
        layout.addWidget(self.thumb)

        name = os.path.basename(video_path)
        if len(name) > 22:
            name = name[:19] + "..."
        self.name_label = QLabel(name)
        self.name_label.setStyleSheet("color: #ffffff; font-size: {}px; background: transparent;".format(wsc(18, zoom)))
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.name_label)

        self._set_duration()
        QTimer.singleShot(100, self._generate_thumb)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def _apply_size(self):
        z = self._zoom
        self.setFixedSize(wsc(160, z), wsc(130, z))

    def update_zoom(self, zoom):
        self._zoom = zoom
        z = zoom
        self._apply_size()
        self._layout.setContentsMargins(wsc(10, z), wsc(10, z), wsc(10, z), wsc(10, z))
        self._layout.setSpacing(wsc(6, z))
        self.thumb.setFixedSize(wsc(140, z), wsc(75, z))
        self.name_label.setStyleSheet("color: #ffffff; font-size: {}px; background: transparent;".format(wsc(18, z)))
        self._generate_thumb()

    def _set_duration(self):
        try:
            cap = cv2.VideoCapture(self.video_path)
            if cap.isOpened():
                fps = cap.get(cv2.CAP_PROP_FPS)
                frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                cap.release()
                if fps > 0:
                    secs = int(frames / fps)
                    m, s = secs // 60, secs % 60
                    self.setToolTip("时长: {:02d}:{:02d}".format(m, s))
        except:
            pass

    def _generate_thumb(self):
        try:
            cap = cv2.VideoCapture(self.video_path)
            if cap.isOpened():
                total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                if total > 0:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, total // 2)
                    ret, frame = cap.read()
                    cap.release()
                    if ret:
                        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        h, w = frame.shape[:2]
                        tw, th = wsc(140, self._zoom), wsc(75, self._zoom)
                        scale = min(tw / w, th / h)
                        nw, nh = int(w * scale), int(h * scale)
                        frame = cv2.resize(frame, (nw, nh))
                        img = QImage(frame.data, nw, nh, 3 * nw, QImage.Format.Format_RGB888)
                        self.thumb.setPixmap(QPixmap.fromImage(img).scaled(
                            tw, th, Qt.AspectRatioMode.KeepAspectRatio,
                            Qt.TransformationMode.SmoothTransformation))
        except:
            pass

    def _preview_video(self):
        os.startfile(self.video_path)

    def _save_video(self):
        name = os.path.basename(self.video_path)
        default_path = os.path.join(os.path.expanduser("~"), "Videos", name)
        path, _ = QFileDialog.getSaveFileName(
            self, "保存视频", default_path, "视频 (*.mp4 *.avi)"
        )
        if path:
            shutil.copy2(self.video_path, path)
            QMessageBox.information(self, "完成", "视频已保存到:\n{}".format(path))

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._preview_video()
        elif event.button() == Qt.MouseButton.RightButton:
            menu = QMenu(self)
            menu.setStyleSheet("""
                QMenu {
                    background-color: rgba(22, 22, 35, 0.95);
                    color: #ffffff;
                    font-size: %dpx;
                    border: 1px solid rgba(255, 255, 255, 0.08);
                    border-radius: 8px;
                    padding: 8px;
                }
                QMenu::item { padding: 10px 30px; border-radius: 6px; background: transparent; }
                QMenu::item:selected { background-color: rgba(0, 217, 255, 0.15); }
            """ % wsc(18, self._zoom))
            preview_action = menu.addAction("▶  预览")
            save_action = menu.addAction("💾  另存为")
            action = menu.exec(event.globalPosition().toPoint())
            if action == preview_action:
                self._preview_video()
            elif action == save_action:
                self._save_video()


class MonitorSelector(QFrame):
    """显示器选择器"""

    def __init__(self, zoom=1.0, parent=None):
        super().__init__(parent)
        self._zoom = zoom
        self.checkboxes = []
        self._hint = None
        self.setup_ui()

    def setup_ui(self):
        z = self._zoom
        self.setStyleSheet("background: transparent; border: none;")
        layout = QVBoxLayout(self)
        self._layout = layout
        layout.setContentsMargins(wsc(10, z), wsc(10, z), wsc(10, z), wsc(10, z))
        layout.setSpacing(wsc(20, z))

        monitors = RecordController.get_monitors()
        for i, m in enumerate(monitors):
            cb = QCheckBox("显示器 {} ({}x{})".format(i + 1, m['width'], m['height']))
            cb.setChecked(i == 0)
            cb.setMinimumHeight(wsc(45, z))
            cb.setStyleSheet(_cb_style(z, font_sz=22, ind_sz=32, spacing=18))
            layout.addWidget(cb)
            self.checkboxes.append(cb)

        self._hint = QLabel("可勾选多个显示器同时录制")
        self._hint.setStyleSheet(
            "color: #808080; font-size: %dpx; margin-top: %dpx; background: transparent;" % (wsc(20, z), wsc(12, z)))
        layout.addWidget(self._hint)

        if len(monitors) <= 1:
            self.hide()

    def get_selected(self):
        return [i + 1 for i, cb in enumerate(self.checkboxes) if cb.isChecked()]

    def setEnabled(self, enabled):
        for cb in self.checkboxes:
            cb.setEnabled(enabled)

    def update_zoom(self, zoom):
        self._zoom = zoom
        z = zoom
        self._layout.setContentsMargins(wsc(10, z), wsc(10, z), wsc(10, z), wsc(10, z))
        self._layout.setSpacing(wsc(20, z))
        for cb in self.checkboxes:
            cb.setMinimumHeight(wsc(45, z))
            cb.setStyleSheet(_cb_style(z, font_sz=22, ind_sz=32, spacing=18))
        if self._hint:
            self._hint.setStyleSheet(
                "color: #808080; font-size: %dpx; margin-top: %dpx; background: transparent;" % (wsc(20, z), wsc(12, z)))


# ────────────────── 主窗口 ──────────────────
class MainWindow(QMainWindow):
    """主窗口 - 系统级等比缩放"""
    _video_ready = Signal(str)  # 线程安全：后台合并完成后通知主线程

    def __init__(self):
        super().__init__()
        self.setWindowTitle("录屏王")

        # 1. 保持底层物理最大尺寸不变 (670x1260)，方便有大屏幕的用户往上拉伸
        self._max_w = sc(_BASE_W)
        self._max_h = sc(_BASE_H)
        self._min_w = int(self._max_w * 0.5)
        self._min_h = int(self._max_h * 0.5)

        self.setMinimumSize(self._min_w, self._min_h)
        self.setMaximumSize(self._max_w, self._max_h)

        # 2. 【核心修改】：将启动时的默认高度缩到 900，并等比算出宽度
        default_h = sc(900)
        default_w = int(default_h * (_BASE_W / _BASE_H))

        # 确保算出来的值没有越界
        default_h = max(self._min_h, min(self._max_h, default_h))
        default_w = max(self._min_w, min(self._max_w, default_w))

        # 3. 以 900 高度启动窗口！
        self.resize(default_w, default_h)

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMouseTracking(True)

        self._drag_pos = None

        # 4. 【核心修改】：程序启动时自动计算缩小比例（约 0.71），这样内部的所有组件、字体都会随之变小！
        self._zoom = default_w / self._max_w

        # 状态保存
        self._current_info_text = "选择录制模式后点击开始"
        self._current_status_key = "idle"
        self._current_status_text = "就绪"

        # 许可证检查
        act = check_activation()
        self._license_activated = act.get("activated", False)

        # 录制目录
        user_videos = os.path.join(os.path.expanduser("~"), "Videos", "录屏王")
        if not os.path.exists(user_videos):
            os.makedirs(user_videos)

        self.recorder = RecordController(user_videos)
        self.recorder.on_status_changed = self._on_status
        self.recorder.on_recording_complete = self._on_complete_threadsafe
        self.record_mode = "fullscreen"

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_time)
        self.elapsed = 0

        self._video_paths = []

        self._video_ready.connect(self._on_complete)

        self._setup_ui()

    # ──────────── nativeEvent: 系统级缩放 + 拖拽 ────────────

    def nativeEvent(self, eventType, message):
        if eventType == b"windows_generic_MSG":
            msg = wintypes.MSG.from_address(int(message))

            if msg.message == WM_NCHITTEST:
                # 提取屏幕坐标（有符号 16 位，支持多显示器负坐标）
                x = msg.lParam & 0xFFFF
                if x > 32767: x -= 65536
                y = (msg.lParam >> 16) & 0xFFFF
                if y > 32767: y -= 65536

                pos = self.mapFromGlobal(QPoint(x, y))
                px, py = pos.x(), pos.y()

                # 1) 精确边缘检测 → 追踪真实可见卡片（self._card）的边缘，无视透明边距！
                b = _BORDER
                card_rect = self._card.geometry()

                on_left = abs(px - card_rect.left()) <= b
                on_right = abs(px - card_rect.right()) <= b
                on_top = abs(py - card_rect.top()) <= b
                on_bottom = abs(py - card_rect.bottom()) <= b

                if on_top and on_left: return True, HTTOPLEFT
                if on_top and on_right: return True, HTTOPRIGHT
                if on_bottom and on_left: return True, HTBOTTOMLEFT
                if on_bottom and on_right: return True, HTBOTTOMRIGHT
                if on_left: return True, HTLEFT
                if on_right: return True, HTRIGHT
                if on_top: return True, HTTOP
                if on_bottom: return True, HTBOTTOM

                # 2) 终极完美标题栏拖拽判定 (无视任何边距干扰！)
                if hasattr(self, '_title_bar') and self._title_bar:
                    # 将全局坐标精确映射到标题栏
                    tb_pos = self._title_bar.mapFromGlobal(QPoint(x, y))
                    if self._title_bar.rect().contains(tb_pos):
                        # 确保点到的不是最小化或关闭按钮
                        child = self._title_bar.childAt(tb_pos)
                        if not isinstance(child, QPushButton):
                            return True, HTCAPTION

                return False, 0

            elif msg.message == WM_SIZING:
                # 在系统层面强制等比缩放
                rect = wintypes.RECT.from_address(msg.lParam)
                side = msg.wParam
                ratio = _BASE_H / _BASE_W

                cur_w = rect.right - rect.left
                cur_w = max(self._min_w, min(self._max_w, cur_w))
                cur_h = int(cur_w * ratio)
                cur_h = max(self._min_h, min(self._max_h, cur_h))
                cur_w = int(cur_h / ratio)

                # 水平：根据拖拽方向决定锚定哪边
                if side in (WMSZ_LEFT, WMSZ_TOPLEFT, WMSZ_BOTTOMLEFT):
                    rect.left = rect.right - cur_w
                else:
                    rect.right = rect.left + cur_w

                # 垂直：根据拖拽方向决定锚定哪边
                if side in (WMSZ_TOP, WMSZ_TOPLEFT, WMSZ_TOPRIGHT):
                    rect.top = rect.bottom - cur_h
                else:
                    rect.bottom = rect.top + cur_h

                return True, 0

            elif msg.message == WM_GETMINMAXINFO:
                info = MINMAXINFO.from_address(msg.lParam)
                info.ptMinTrackSize.x = self._min_w
                info.ptMinTrackSize.y = self._min_h
                info.ptMaxTrackSize.x = self._max_w
                info.ptMaxTrackSize.y = self._max_h
                return True, 0

        return super().nativeEvent(eventType, message)

    # ──────────── resizeEvent → update_ui_scale ────────────

    def resizeEvent(self, event):
        super().resizeEvent(event)
        new_zoom = max(0.5, min(1.0, self.width() / self._max_w))
        if abs(new_zoom - self._zoom) > 0.01:
            self._zoom = new_zoom
            self.update_ui_scale(new_zoom)

    def update_ui_scale(self, zoom):
        """在现有控件上原地更新尺寸/字体，不销毁不重建"""
        z = zoom

        # 标题栏
        self._title_bar.update_zoom(z)

        # 内容区布局
        self._content_layout.setContentsMargins(wsc(30, z), wsc(25, z), wsc(30, z), wsc(25, z))
        self._content_layout.setSpacing(wsc(18, z))

        # 状态区
        self.indicator.update_zoom(z)
        colors = {"recording": "#e94560", "paused": "#ffc107", "idle": "#00d9ff"}
        self.status_label.setStyleSheet(
            "color: {}; font-size: {}px; font-weight: bold; margin-left: {}px; background: transparent;".format(
                colors.get(self._current_status_key, "#00d9ff"), wsc(30, z), wsc(12, z)))

        # 时间显示
        self.time_display.update_zoom(z)

        # 录制信息
        self._info_layout.setContentsMargins(wsc(18, z), wsc(14, z), wsc(18, z), wsc(14, z))
        self.info_label.setStyleSheet(
            "color: #a0a0a0; font-size: {}px; background: transparent; border: none;".format(wsc(22, z)))

        # 标签
        for lbl in (self._mode_label, self._video_label):
            lbl.setStyleSheet("color: #a0a0a0; font-size: {}px; font-weight: bold; background: transparent;".format(wsc(22, z)))
        self.monitor_label.setStyleSheet("color: #a0a0a0; font-size: {}px; font-weight: bold; background: transparent;".format(wsc(22, z)))

        # 模式按钮
        self.fullscreen_btn.update_zoom(z)
        self.region_btn.update_zoom(z)
        self._mode_layout.setSpacing(wsc(18, z))

        # 音频勾选框
        self.mic_check.setStyleSheet(_cb_style(z, font_sz=20, ind_sz=26))
        self.sys_check.setStyleSheet(_cb_style(z, font_sz=20, ind_sz=26))

        # 显示器选择器
        self.monitor_selector.update_zoom(z)

        # 控制按钮：因为现在都是自定义组件，直接调用 update_zoom 即可
        self.pause_btn.update_zoom(z)
        self.record_btn.update_zoom(z)
        self.stop_btn.update_zoom(z)
        self._button_layout.setSpacing(wsc(20, z))

        # 滚动区
        self._scroll_area.setFixedHeight(wsc(150, z))
        self._scroll_area.setStyleSheet("""
            QScrollArea { background-color: rgba(0, 0, 0, 0.25); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; }
            QScrollBar:horizontal { height: %dpx; background: rgba(255, 255, 255, 0.02); border-radius: %dpx; }
            QScrollBar::handle:horizontal { background: rgba(255, 255, 255, 0.15); border-radius: %dpx; min-width: %dpx; }
            QScrollBar::handle:horizontal:hover { background: rgba(0, 217, 255, 0.5); }
        """ % (wsc(10, z), wsc(5, z), wsc(5, z), wsc(30, z)))

        self.video_layout.setContentsMargins(wsc(12, z), wsc(12, z), wsc(12, z), wsc(12, z))
        self.video_layout.setSpacing(wsc(12, z))

        # 视频卡片
        for i in range(self.video_layout.count()):
            item = self.video_layout.itemAt(i)
            if item and item.widget() and isinstance(item.widget(), VideoCard):
                item.widget().update_zoom(z)

        # 底部提示
        self._bottom_hint.setStyleSheet("color: #808080; font-size: {}px; background: transparent;".format(wsc(20, z)))

        # 全局样式
        self._apply_styles(z)

    # ──────────── UI 构建（仅初始时调用一次）────────────

    def _setup_ui(self):
        central = QWidget()
        central.setObjectName("centralWidget")
        self.setCentralWidget(central)

        layout = QVBoxLayout(central)
        layout.setContentsMargins(sc(18), sc(18), sc(18), sc(18))

        self._card = BokehBackground(self)
        self._card.setObjectName("mainCard")
        layout.addWidget(self._card)

        self._build_content(self._zoom)

    def _build_content(self, zoom):
        z = zoom
        card = self._card

        cl = QVBoxLayout(card)
        cl.setContentsMargins(0, 0, 0, 0)

        # 标题栏
        self._title_bar = TitleBar("录屏王", zoom=z)
        self._title_bar.close_clicked.connect(self._on_close)
        self._title_bar.minimize_clicked.connect(self.showMinimized)
        # 【新增这行】：点击订阅按钮时，直接调用本类中的 _show_payment_dialog 方法
        self._title_bar.subscribe_clicked.connect(self._show_payment_dialog)
        cl.addWidget(self._title_bar)

        # 内容区域
        content = QWidget()
        content.setStyleSheet("background: transparent;")
        self._content_layout = QVBoxLayout(content)
        ct = self._content_layout
        ct.setContentsMargins(wsc(30, z), wsc(25, z), wsc(30, z), wsc(25, z))
        ct.setSpacing(wsc(18, z))

        # 状态区
        sframe = QFrame()
        sframe.setStyleSheet("background: transparent;")
        sl = QHBoxLayout(sframe)
        sl.setContentsMargins(0, 0, 0, 0)

        self.indicator = StatusIndicator(zoom=z)
        sl.addWidget(self.indicator)

        self.status_label = QLabel("就绪")
        self.status_label.setObjectName("statusLabel")
        sl.addWidget(self.status_label)
        sl.addStretch()
        ct.addWidget(sframe)

        # 时间显示
        self.time_display = TimeDisplay(zoom=z)
        self.time_display.set_time(int(self.elapsed))
        ct.addWidget(self.time_display)

        # 录制信息
        self.info_frame = QFrame()
        self.info_frame.setStyleSheet(
            "QFrame { background-color: rgba(255, 255, 255, 0.04); border-radius: 10px; border: 1px solid rgba(255, 255, 255, 0.06); }")
        self._info_layout = QVBoxLayout(self.info_frame)
        self._info_layout.setContentsMargins(wsc(18, z), wsc(14, z), wsc(18, z), wsc(14, z))
        self.info_label = QLabel(self._current_info_text)
        self.info_label.setStyleSheet(
            "color: #a0a0a0; font-size: {}px; background: transparent; border: none;".format(wsc(22, z)))
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._info_layout.addWidget(self.info_label)
        ct.addWidget(self.info_frame)

        ct.addWidget(self._line())

        # 模式选择
        self._mode_label = QLabel("录制模式")
        self._mode_label.setStyleSheet("color: #a0a0a0; font-size: {}px; font-weight: bold; background: transparent;".format(wsc(22, z)))
        ct.addWidget(self._mode_label)
        self._mode_layout = QHBoxLayout()
        self._mode_layout.setSpacing(wsc(18, z))

        self.fullscreen_btn = ModeButton("全屏录制", "🖥", zoom=z)
        self.fullscreen_btn.setChecked(True)
        self.fullscreen_btn.clicked.connect(lambda: self._set_mode("fullscreen"))
        self._mode_layout.addWidget(self.fullscreen_btn)

        self.region_btn = ModeButton("区域录制", "📐", zoom=z)
        self.region_btn.clicked.connect(lambda: self._set_mode("region"))
        self._mode_layout.addWidget(self.region_btn)
        ct.addLayout(self._mode_layout)

        # 显示器选择
        self.monitor_label = QLabel("选择显示器（可多选）")
        self.monitor_label.setStyleSheet("color: #a0a0a0; font-size: {}px; font-weight: bold; background: transparent;".format(wsc(22, z)))
        ct.addWidget(self.monitor_label)
        self.monitor_selector = MonitorSelector(zoom=z)
        ct.addWidget(self.monitor_selector)

        ct.addWidget(self._line())

        ct.addSpacing(wsc(12, z))

        # 音频控制
        audio_layout = QHBoxLayout()
        audio_layout.setSpacing(wsc(24, z))

        self.mic_check = QCheckBox("🎤  麦克风")
        self.mic_check.setChecked(True)
        self.mic_check.stateChanged.connect(self._on_audio_toggle)
        self.mic_check.setStyleSheet(_cb_style(z, font_sz=20, ind_sz=26))
        audio_layout.addWidget(self.mic_check)

        self.sys_check = QCheckBox("🔊  系统声音")
        self.sys_check.setChecked(True)
        self.sys_check.stateChanged.connect(self._on_audio_toggle)
        self.sys_check.setStyleSheet(_cb_style(z, font_sz=20, ind_sz=26))
        audio_layout.addWidget(self.sys_check)

        audio_layout.addStretch()
        ct.addLayout(audio_layout)

        # 控制按钮
        self._button_layout = QHBoxLayout()
        self._button_layout.setSpacing(wsc(20, z))

        # 使用与“全屏录制”一模一样的 ModeButton 组件
        self.pause_btn = ModeButton("暂停", "⏸️", zoom=z)
        self.pause_btn.setEnabled(False)
        self.pause_btn.clicked.connect(self._toggle_pause)
        self._button_layout.addWidget(self.pause_btn)

        self.record_btn = RecordButton(zoom=z)
        self.record_btn.clicked.connect(self._toggle_record)
        self._button_layout.addWidget(self.record_btn)

        self.stop_btn = ModeButton("停止", "⏹️", zoom=z)
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._stop_record)
        self._button_layout.addWidget(self.stop_btn)
        ct.addLayout(self._button_layout)

        ct.addWidget(self._line())

        # 视频列表
        self._video_label = QLabel("已录制视频（点击另存为）")
        self._video_label.setStyleSheet("color: #a0a0a0; font-size: {}px; font-weight: bold; background: transparent;".format(wsc(22, z)))
        ct.addWidget(self._video_label)

        self._scroll_area = QScrollArea()
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setFixedHeight(wsc(150, z))
        self._scroll_area.setStyleSheet("""
            QScrollArea { background-color: rgba(0, 0, 0, 0.25); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; }
            QScrollBar:horizontal { height: %dpx; background: rgba(255, 255, 255, 0.02); border-radius: %dpx; }
            QScrollBar::handle:horizontal { background: rgba(255, 255, 255, 0.15); border-radius: %dpx; min-width: %dpx; }
            QScrollBar::handle:horizontal:hover { background: rgba(0, 217, 255, 0.5); }
        """ % (wsc(10, z), wsc(5, z), wsc(5, z), wsc(30, z)))

        self.video_container = QWidget()
        self.video_container.setStyleSheet("background: transparent;")
        self.video_layout = QHBoxLayout(self.video_container)
        self.video_layout.setContentsMargins(wsc(12, z), wsc(12, z), wsc(12, z), wsc(12, z))
        self.video_layout.setSpacing(wsc(12, z))
        self.video_layout.addStretch()

        for path in self._video_paths:
            if os.path.exists(path):
                card_item = VideoCard(path, zoom=z)
                self.video_layout.insertWidget(self.video_layout.count() - 1, card_item)

        self._scroll_area.setWidget(self.video_container)
        ct.addWidget(self._scroll_area)

        # 底部提示
        self._bottom_hint = QLabel("F9 开始/停止  |  F10 暂停/继续  |  ESC 退出")
        self._bottom_hint.setStyleSheet("color: #808080; font-size: {}px; background: transparent;".format(wsc(20, z)))
        self._bottom_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ct.addWidget(self._bottom_hint)

        cl.addWidget(content)
        self._apply_styles(z)


    def _line(self):
        l = QFrame()
        l.setFixedHeight(1)
        l.setStyleSheet("background-color: rgba(255, 255, 255, 0.06);")
        return l

    def _apply_styles(self, z=1.0):
        self.setStyleSheet("""
            #centralWidget { background: transparent; }
            #mainCard { background-color: transparent; }
            #statusLabel { color: #00d9ff; font-size: %dpx; font-weight: bold; margin-left: %dpx; background: transparent; }
            QPushButton {
                background-color: rgba(255, 255, 255, 0.15);
                color: #ffffff;
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 12px;
                padding: %dpx %dpx;
                font-size: %dpx;
                font-weight: bold;
            }
            QPushButton:hover { background-color: rgba(0, 217, 255, 0.2); border-color: #00d9ff; }
            QPushButton:disabled {
                background-color: rgba(255, 255, 255, 0.08);
                color: #7a7a9a;
                border: 1px solid rgba(255, 255, 255, 0.1);
            }
            QToolTip { font-size: %dpx; padding: 6px 10px; border-radius: 6px; background-color: #1a1a2e; color: white; }
            QMessageBox { font-size: %dpx; }
        """ % (wsc(30, z), wsc(12, z), wsc(14, z), wsc(30, z), wsc(24, z), wsc(20, z), wsc(20, z)))

    # ──────────── 业务逻辑（全盘保留）────────────

    def _set_mode(self, mode):
        self.record_mode = mode
        self.fullscreen_btn.setChecked(mode == "fullscreen")
        self.region_btn.setChecked(mode == "region")
        self.monitor_label.setVisible(mode == "fullscreen")
        self.monitor_selector.setVisible(mode == "fullscreen")

        if mode == "fullscreen":
            selected = self.monitor_selector.get_selected()
            self.info_label.setText("已选择 {} 个显示器，点击开始录制".format(len(selected)))
            self._current_info_text = self.info_label.text()
        else:
            self.info_label.setText("点击开始后拖拽选择录制区域")
            self._current_info_text = self.info_label.text()

    def _toggle_record(self):
        if self.recorder.is_recording:
            self._stop_record()
        else:
            if not self._license_activated:
                self._show_payment_dialog()
                return
            self._start_record()

    def _start_record(self):
        # 设置音频开关
        self.recorder.record_mic = self.mic_check.isChecked()
        self.recorder.record_system = self.sys_check.isChecked()

        if self.record_mode == "region":
            self.info_label.setText("请在屏幕上拖拽选择录制区域...")
            self._current_info_text = self.info_label.text()
            from PySide6.QtWidgets import QApplication
            QApplication.processEvents()

            region = select_area()
            if region:
                x, y, w, h = region
                self.recorder.set_region(x, y, w, h)
                self.info_label.setText("区域录制: ({}, {}) {}x{}".format(x, y, w, h))
                self._current_info_text = self.info_label.text()
            else:
                self.info_label.setText("已取消选择")
                self._current_info_text = self.info_label.text()
                return
        else:
            self.recorder.set_fullscreen()
            selected = self.monitor_selector.get_selected()
            self.recorder.set_monitors(selected)

            if len(selected) == 1:
                self.info_label.setText("正在录制显示器 {}...".format(selected[0]))
            else:
                self.info_label.setText("正在录制 {} 个显示器...".format(len(selected)))
            self._current_info_text = self.info_label.text()

        paths = self.recorder.start()
        if paths:
            self.elapsed = 0
            self.timer.start(100)
            self.record_btn.set_recording(True)
            self.pause_btn.setEnabled(True)
            self.stop_btn.setEnabled(True)
            self.fullscreen_btn.setEnabled(False)
            self.region_btn.setEnabled(False)
            self.monitor_selector.setEnabled(False)
            self._update_status("recording", "录制中")

    def _stop_record(self):
        self.info_label.setText("正在保存视频...")
        self._current_info_text = self.info_label.text()
        from PySide6.QtWidgets import QApplication
        QApplication.processEvents()

        paths = self.recorder.stop()
        self.timer.stop()

        self.record_btn.set_recording(False)
        self.pause_btn.setEnabled(False)
        self.pause_btn.setText("⏸  暂停")
        self.stop_btn.setEnabled(False)
        self.fullscreen_btn.setEnabled(True)
        self.region_btn.setEnabled(True)
        self.monitor_selector.setEnabled(True)

        self._update_status("idle", "就绪")

        # 如果有音频需要合并，显示提示 (合并会在后台线程执行)
        has_audio = (self.mic_check.isChecked() or self.sys_check.isChecked())
        if has_audio:
            self.info_label.setText("正在合并音视频，请稍候...")
        else:
            self.info_label.setText("录制完成，共 {} 个视频".format(len(paths)))
        self._current_info_text = self.info_label.text()
        self.time_display.set_time(0)

    def _toggle_pause(self):
        if self.recorder.is_paused:
            self.recorder.is_paused = False
            self.pause_btn.setText("⏸  暂停")
            self._update_status("recording", "录制中")
            self.timer.start(100)
        else:
            self.recorder.is_paused = True
            self.pause_btn.setText("▶  继续")
            self._update_status("paused", "已暂停")
            self.timer.stop()

    def _update_time(self):
        self.elapsed = self.recorder.get_duration()
        self.time_display.set_time(int(self.elapsed))

    def _update_status(self, status, text):
        self.status_label.setText(text)
        self.indicator.set_status(status)
        self._current_status_key = status
        self._current_status_text = text

        colors = {"recording": "#e94560", "paused": "#ffc107", "idle": "#00d9ff"}
        self.status_label.setStyleSheet(
            "color: {}; font-size: {}px; font-weight: bold; margin-left: {}px; background: transparent;".format(
                colors.get(status, "#ffffff"), wsc(17, self._zoom), wsc(12, self._zoom)))

    def _on_status(self, status):
        pass

    def _show_payment_dialog(self):
        from ui.pay_dialog import PayDialog
        self._pay_dialog = PayDialog(self)
        self._pay_dialog.payment_success.connect(self._on_payment_success)
        self._pay_dialog.show()

    def _on_payment_success(self):
        self._license_activated = True
        self._start_record()

    def _on_audio_toggle(self):
        """实时切换麦克风/系统声音静音"""
        cap = getattr(self.recorder, '_audio_capture', None)
        if cap:
            cap.set_mute("mic", not self.mic_check.isChecked())
            cap.set_mute("sys", not self.sys_check.isChecked())

    def _on_complete_threadsafe(self, path):
        """后台线程调用 → 通过信号转发到主线程"""
        self._video_ready.emit(path)

    def _on_complete(self, path):
        if os.path.exists(path):
            self._video_paths.append(path)
            card = VideoCard(path, zoom=self._zoom)
            self.video_layout.insertWidget(self.video_layout.count() - 1, card)
            # 合并完成后更新提示文字
            self.info_label.setText("录制完成，共 {} 个视频".format(len(self._video_paths)))
            self._current_info_text = self.info_label.text()

    def _on_close(self):
        self.close()

    # === 拖拽（fallback，nativeEvent 的 HTCAPTION 是主路径）===
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if self._drag_pos:
            self.move(event.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None

    def closeEvent(self, event):
        if self.recorder.is_recording:
            reply = QMessageBox.question(
                self, "确认退出",
                "正在录制中，确定要退出吗？\n录制将被保存。",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.hide()  # 【核心修复】：先瞬间隐藏主窗口，眼不见为净！
                self._stop_record()
                self.recorder.close()  # 后台慢慢释放资源，用户完全感觉不到卡顿
                event.accept()
            else:
                event.ignore()
        else:
            self.hide()  # 【核心修复】：先瞬间隐藏主窗口！
            self.recorder.close()  # 这里卡住 1 秒也没关系，因为界面已经秒退了
            event.accept()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_F9:
            self._toggle_record()
        elif event.key() == Qt.Key.Key_F10:
            if self.recorder.is_recording:
                self._toggle_pause()
        elif event.key() == Qt.Key.Key_Escape:
            if not self.recorder.is_recording:
                self.close()
