# -*- coding: utf-8 -*-
"""
主窗口 - 顶级玻璃质感UI (光斑背景 + 半透明控件，业务逻辑全保留)
"""
import os
import shutil
import random
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QScrollArea, QFileDialog, QCheckBox, QMessageBox, QMenu
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap, QImage, QColor, QPainter, QRadialGradient

import cv2

from ui.widgets import RecordButton, ModeButton, StatusIndicator, TimeDisplay, TitleBar
from ui.styles import COLORS, BUTTON_STYLES
from recorder.controller import RecordController
from recorder.area_selector import select_area
from license.activation import check_activation
from utils.config import sc


# ────────────────── 动态失焦光斑背景底层 ──────────────────
class BokehBackground(QWidget):
    """纯代码渲染的动态失焦光斑背景 (适配主窗口圆角)"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        # 主窗口背景，带一点极弱的边框高光
        self.setStyleSheet(
            "background-color: #1a1a2e; border-radius: 16px; border: 1px solid rgba(255, 255, 255, 0.05);")

        self._particles = []
        self._num_particles = 3  # 恢复 6 个光斑
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
            radius = random.randint(sc(80), sc(220))
            x, y = random.randint(0, w), random.randint(0, h)
            vx, vy = random.uniform(-0.5, 0.5), random.uniform(-0.5, 0.5)
            color = random.choice(self._colors)
            self._particles.append({'x': x, 'y': y, 'vx': vx, 'vy': vy, 'radius': radius, 'color': color})
        self._initialized = True

    def _update_particles(self):
        if not self._initialized: return
        w, h = self.width(), self.height()
        for p in self._particles:
            p['x'] += p['vx']
            p['y'] += p['vy']
            if p['x'] - p['radius'] > w or p['x'] + p['radius'] < 0: p['vx'] *= -1
            if p['y'] - p['radius'] > h or p['y'] + p['radius'] < 0: p['vy'] *= -1
        self.update()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if not self._initialized: self._init_particles()

    def paintEvent(self, event):
        super().paintEvent(event)
        if not self._initialized: return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        for p in self._particles:
            gradient = QRadialGradient(p['x'], p['y'], p['radius'])
            center_color = p['color']
            edge_color = QColor(center_color)
            edge_color.setAlpha(0)
            gradient.setColorAt(0, center_color)
            gradient.setColorAt(0.7, center_color)
            gradient.setColorAt(1, edge_color)
            painter.setBrush(gradient)
            painter.drawEllipse(int(p['x'] - p['radius']), int(p['y'] - p['radius']), int(p['radius'] * 2),
                                int(p['radius'] * 2))


# ────────────────── 视频卡片 (毛玻璃升级版) ──────────────────
class VideoCard(QFrame):
    """视频卡片"""

    def __init__(self, video_path, parent=None):
        super().__init__(parent)
        self.video_path = video_path
        self.setObjectName("videoCard")
        self.setFixedSize(sc(160), sc(130))
        # ✨ 升级为半透明毛玻璃质感
        self.setStyleSheet("""
            #videoCard { background-color: rgba(255, 255, 255, 0.04); border-radius: 12px; border: 1px solid rgba(255, 255, 255, 0.06); }
            #videoCard:hover { border-color: #00d9ff; background-color: rgba(0, 217, 255, 0.05); }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(sc(10), sc(10), sc(10), sc(10))
        layout.setSpacing(sc(6))

        self.thumb = QLabel()
        self.thumb.setFixedSize(sc(140), sc(75))
        # 缩略图底色改为深色半透明
        self.thumb.setStyleSheet("background-color: rgba(0, 0, 0, 0.3); border-radius: 6px;")
        self.thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumb.setText("📹")
        layout.addWidget(self.thumb)

        name = os.path.basename(video_path)
        if len(name) > 22:
            name = name[:19] + "..."
        self.name_label = QLabel(name)
        self.name_label.setStyleSheet("color: #ffffff; font-size: {}px; background: transparent;".format(sc(18)))
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.name_label)

        self._set_duration()
        QTimer.singleShot(100, self._generate_thumb)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

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
                        tw, th = sc(140), sc(75)
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
            # ✨ 右键菜单毛玻璃风格
            menu.setStyleSheet("""
                QMenu {
                    background-color: rgba(22, 22, 35, 0.95);
                    color: #ffffff;
                    font-size: %dpx;
                    border: 1px solid rgba(255, 255, 255, 0.08);
                    border-radius: 8px;
                    padding: 8px;
                }
                QMenu::item {
                    padding: 10px 30px;
                    border-radius: 6px;
                    background: transparent;
                }
                QMenu::item:selected {
                    background-color: rgba(0, 217, 255, 0.15);
                }
            """ % sc(18))
            preview_action = menu.addAction("▶  预览")
            save_action = menu.addAction("💾  另存为")
            action = menu.exec(event.globalPosition().toPoint())
            if action == preview_action:
                self._preview_video()
            elif action == save_action:
                self._save_video()


class MonitorSelector(QFrame):
    """显示器选择器"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.checkboxes = []
        self.setup_ui()

    def setup_ui(self):
        self.setStyleSheet("background: transparent; border: none;")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(sc(10), sc(10), sc(10), sc(10))
        layout.setSpacing(sc(20))

        monitors = RecordController.get_monitors()
        for i, m in enumerate(monitors):
            cb = QCheckBox("显示器 {} ({}x{})".format(i + 1, m['width'], m['height']))
            cb.setChecked(i == 0)
            cb.setMinimumHeight(sc(45))
            # ✨ 复选框玻璃化：框框改成半透明
            cb.setStyleSheet("""
                QCheckBox { color: #ffffff; font-size: %dpx; spacing: %dpx; }
                QCheckBox::indicator { width: %dpx; height: %dpx; border-radius: %dpx;
                    border: 1px solid rgba(255, 255, 255, 0.2); background-color: rgba(0, 0, 0, 0.2); }
                QCheckBox::indicator:checked { background-color: #00d9ff; border-color: #00d9ff; }
                QCheckBox::indicator:hover { border-color: #00d9ff; }
            """ % (sc(22), sc(18), sc(32), sc(32), sc(10)))
            layout.addWidget(cb)
            self.checkboxes.append(cb)

        hint = QLabel("可勾选多个显示器同时录制")
        hint.setStyleSheet(
            "color: #808080; font-size: %dpx; margin-top: %dpx; background: transparent;" % (sc(20), sc(12)))
        layout.addWidget(hint)

        if len(monitors) <= 1:
            self.hide()

    def get_selected(self):
        return [i + 1 for i, cb in enumerate(self.checkboxes) if cb.isChecked()]

    def setEnabled(self, enabled):
        for cb in self.checkboxes:
            cb.setEnabled(enabled)


# ────────────────── 主窗口 ──────────────────
class MainWindow(QMainWindow):
    """主窗口"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("录屏王")
        self.setMinimumSize(sc(670), sc(1260))
        self.resize(sc(670), sc(1260))

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self._drag_pos = None

        # 许可证检查
        act = check_activation()
        self._license_activated = act.get("activated", False)

        # 录制目录
        user_videos = os.path.join(os.path.expanduser("~"), "Videos", "录屏王")
        if not os.path.exists(user_videos):
            os.makedirs(user_videos)

        self.recorder = RecordController(user_videos)
        self.recorder.on_status_changed = self._on_status
        self.recorder.on_recording_complete = self._on_complete
        self.record_mode = "fullscreen"

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_time)
        self.elapsed = 0

        self._setup_ui()

    def _setup_ui(self):
        central = QWidget()
        central.setObjectName("centralWidget")
        self.setCentralWidget(central)

        layout = QVBoxLayout(central)
        layout.setContentsMargins(sc(18), sc(18), sc(18), sc(18))

        # ✨ 替换：将死板的 QFrame 换成动态光斑底板 BokehBackground
        card = BokehBackground(self)
        card.setObjectName("mainCard")
        layout.addWidget(card)

        cl = QVBoxLayout(card)
        cl.setContentsMargins(0, 0, 0, 0)

        # 标题栏
        title = TitleBar("录屏王")
        title.close_clicked.connect(self._on_close)
        title.minimize_clicked.connect(self.showMinimized)
        cl.addWidget(title)

        # 内容区域
        content = QWidget()
        content.setStyleSheet("background: transparent;")  # 确保内容区透明，露出光斑
        ct = QVBoxLayout(content)
        ct.setContentsMargins(sc(30), sc(25), sc(30), sc(25))
        ct.setSpacing(sc(18))

        # 状态区
        sframe = QFrame()
        sframe.setStyleSheet("background: transparent;")
        sl = QHBoxLayout(sframe)
        sl.setContentsMargins(0, 0, 0, 0)

        self.indicator = StatusIndicator()
        sl.addWidget(self.indicator)

        self.status_label = QLabel("就绪")
        self.status_label.setObjectName("statusLabel")
        sl.addWidget(self.status_label)
        sl.addStretch()
        ct.addWidget(sframe)

        # 时间显示
        self.time_display = TimeDisplay()
        ct.addWidget(self.time_display)

        # 录制信息
        self.info_frame = QFrame()
        # ✨ 升级为半透明毛玻璃框
        self.info_frame.setStyleSheet(
            "QFrame { background-color: rgba(255, 255, 255, 0.04); border-radius: 10px; border: 1px solid rgba(255, 255, 255, 0.06); }")
        info_layout = QVBoxLayout(self.info_frame)
        info_layout.setContentsMargins(sc(18), sc(14), sc(18), sc(14))
        self.info_label = QLabel("选择录制模式后点击开始")
        self.info_label.setStyleSheet(
            "color: #a0a0a0; font-size: %dpx; background: transparent; border: none;" % sc(22))
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_layout.addWidget(self.info_label)
        ct.addWidget(self.info_frame)

        ct.addWidget(self._line())

        # 模式选择
        ct.addWidget(self._label("录制模式"))
        ml = QHBoxLayout()
        ml.setSpacing(sc(18))

        self.fullscreen_btn = ModeButton("全屏录制", "🖥")
        self.fullscreen_btn.setChecked(True)
        self.fullscreen_btn.clicked.connect(lambda: self._set_mode("fullscreen"))
        ml.addWidget(self.fullscreen_btn)

        self.region_btn = ModeButton("区域录制", "📐")
        self.region_btn.clicked.connect(lambda: self._set_mode("region"))
        ml.addWidget(self.region_btn)
        ct.addLayout(ml)

        # 显示器选择
        self.monitor_label = self._label("选择显示器（可多选）")
        ct.addWidget(self.monitor_label)
        self.monitor_selector = MonitorSelector()
        ct.addWidget(self.monitor_selector)

        ct.addWidget(self._line())

        # 控制按钮
        ct.addSpacing(sc(12))

        bl = QHBoxLayout()
        bl.setSpacing(sc(20))

        self.pause_btn = QPushButton("⏸  暂停")
        self.pause_btn.setEnabled(False)
        self.pause_btn.clicked.connect(self._toggle_pause)
        self.pause_btn.setFixedHeight(sc(70))
        bl.addWidget(self.pause_btn)

        self.record_btn = RecordButton()
        self.record_btn.clicked.connect(self._toggle_record)
        bl.addWidget(self.record_btn)

        self.stop_btn = QPushButton("⏹  停止")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._stop_record)
        self.stop_btn.setFixedHeight(sc(70))
        bl.addWidget(self.stop_btn)

        ct.addLayout(bl)

        ct.addWidget(self._line())

        # 视频列表
        ct.addWidget(self._label("已录制视频（点击另存为）"))

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFixedHeight(sc(150))

        # ✨ 滚动区域：增加暗黑半透明底色，营造“容器凹槽”感
        scroll.setStyleSheet("""
                    QScrollArea { background-color: rgba(0, 0, 0, 0.25); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; }
                    QScrollBar:horizontal { height: %dpx; background: rgba(255, 255, 255, 0.02); border-radius: %dpx; }
                    QScrollBar::handle:horizontal { background: rgba(255, 255, 255, 0.15); border-radius: %dpx; min-width: %dpx; }
                    QScrollBar::handle:horizontal:hover { background: rgba(0, 217, 255, 0.5); }
                """ % (sc(10), sc(5), sc(5), sc(30)))

        self.video_container = QWidget()
        self.video_container.setStyleSheet("background: transparent;")
        self.video_layout = QHBoxLayout(self.video_container)
        self.video_layout.setContentsMargins(sc(12), sc(12), sc(12), sc(12))
        self.video_layout.setSpacing(sc(12))
        self.video_layout.addStretch()
        scroll.setWidget(self.video_container)
        ct.addWidget(scroll)

        # 底部提示
        hint = QLabel("F9 开始/停止  |  F10 暂停/继续  |  ESC 退出")
        hint.setStyleSheet("color: #808080; font-size: %dpx; background: transparent;" % sc(20))
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ct.addWidget(hint)

        cl.addWidget(content)
        self._apply_styles()

    def _label(self, text):
        l = QLabel(text)
        l.setStyleSheet("color: #a0a0a0; font-size: %dpx; font-weight: bold; background: transparent;" % sc(22))
        return l

    def _line(self):
        l = QFrame()
        l.setFixedHeight(1)
        # ✨ 分割线减弱透明度，更柔和
        l.setStyleSheet("background-color: rgba(255, 255, 255, 0.06);")
        return l

    def _apply_styles(self):
        # ✨ 全局按钮玻璃质感升级
        self.setStyleSheet("""
            #centralWidget { background: transparent; }
            #mainCard { background-color: transparent; } 
            #statusLabel { color: #00d9ff; font-size: %dpx; font-weight: bold; margin-left: %dpx; background: transparent; }

            /* 按钮半透明玻璃风格 (正常状态，提升实体感) */
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

            /* ✨ 核心修复：禁用状态（未开始录制时）的按钮，也要有明显的半透明底色！ */
            QPushButton:disabled { 
                background-color: rgba(255, 255, 255, 0.08); /* 从0.03提高到0.08，让框框显形 */
                color: #7a7a9a; /* 文字保持灰暗，表示当前不可点击 */
                border: 1px solid rgba(255, 255, 255, 0.1); 
            }

            QToolTip { font-size: %dpx; padding: 6px 10px; border-radius: 6px; background-color: #1a1a2e; color: white; }
            QMessageBox { font-size: %dpx; }
        """ % (sc(30), sc(12), sc(14), sc(30), sc(24), sc(20), sc(20)))

    # ──────────── 以下业务逻辑全盘、一字不差保留 ────────────

    def _set_mode(self, mode):
        self.record_mode = mode
        self.fullscreen_btn.setChecked(mode == "fullscreen")
        self.region_btn.setChecked(mode == "region")
        self.monitor_label.setVisible(mode == "fullscreen")
        self.monitor_selector.setVisible(mode == "fullscreen")

        if mode == "fullscreen":
            selected = self.monitor_selector.get_selected()
            self.info_label.setText("已选择 {} 个显示器，点击开始录制".format(len(selected)))
        else:
            self.info_label.setText("点击开始后拖拽选择录制区域")

    def _toggle_record(self):
        if self.recorder.is_recording:
            self._stop_record()
        else:
            if not self._license_activated:
                self._show_payment_dialog()
                return
            self._start_record()

    def _start_record(self):
        if self.record_mode == "region":
            self.info_label.setText("请在屏幕上拖拽选择录制区域...")
            from PySide6.QtWidgets import QApplication
            QApplication.processEvents()

            region = select_area()
            if region:
                x, y, w, h = region
                self.recorder.set_region(x, y, w, h)
                self.info_label.setText("区域录制: ({}, {}) {}x{}".format(x, y, w, h))
            else:
                self.info_label.setText("已取消选择")
                return
        else:
            self.recorder.set_fullscreen()
            selected = self.monitor_selector.get_selected()
            self.recorder.set_monitors(selected)

            if len(selected) == 1:
                self.info_label.setText("正在录制显示器 {}...".format(selected[0]))
            else:
                self.info_label.setText("正在录制 {} 个显示器...".format(len(selected)))

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
        self.info_label.setText("录制完成，共 {} 个视频".format(len(paths)))
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

        colors = {"recording": "#e94560", "paused": "#ffc107", "idle": "#00d9ff"}
        self.status_label.setStyleSheet(
            "color: {}; font-size: {}px; font-weight: bold; margin-left: {}px; background: transparent;".format(
                colors.get(status, "#ffffff"), sc(17), sc(12)))

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

    def _on_complete(self, path):
        if os.path.exists(path):
            card = VideoCard(path)
            self.video_layout.insertWidget(0, card)

    def _on_close(self):
        self.close()

    # === 拖拽 ===
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
                self._stop_record()
                self.recorder.close()
                event.accept()
            else:
                event.ignore()
        else:
            self.recorder.close()
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