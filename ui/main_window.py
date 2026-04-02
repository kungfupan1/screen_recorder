# -*- coding: utf-8 -*-
"""
主窗口 - 完善的录屏界面
"""
import os
import shutil
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QScrollArea, QFileDialog, QCheckBox, QMessageBox, QMenu
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap, QImage
import cv2

from ui.widgets import RecordButton, ModeButton, StatusIndicator, TimeDisplay, TitleBar
from ui.styles import COLORS
from recorder.controller import RecordController
from recorder.area_selector import select_area


class VideoCard(QFrame):
    """视频卡片"""

    def __init__(self, video_path, parent=None):
        super().__init__(parent)
        self.video_path = video_path
        self.setObjectName("videoCard")
        self.setFixedSize(160, 130)  # 稍微大一点
        self.setStyleSheet("""
            #videoCard { background-color: #0f3460; border-radius: 12px; border: 1px solid #2a2a4a; }
            #videoCard:hover { border-color: #00d9ff; background-color: #1a4a80; }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)

        self.thumb = QLabel()
        self.thumb.setFixedSize(140, 75)
        self.thumb.setStyleSheet("background-color: #16213e; border-radius: 6px;")
        self.thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumb.setText("📹")
        layout.addWidget(self.thumb)

        name = os.path.basename(video_path)
        if len(name) > 22:
            name = name[:19] + "..."
        self.name_label = QLabel(name)
        self.name_label.setStyleSheet("color: #ffffff; font-size: 18px; background: transparent;")
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
                        scale = min(140/w, 75/h)
                        nw, nh = int(w*scale), int(h*scale)
                        frame = cv2.resize(frame, (nw, nh))
                        img = QImage(frame.data, nw, nh, 3*nw, QImage.Format.Format_RGB888)
                        self.thumb.setPixmap(QPixmap.fromImage(img).scaled(
                            140, 75, Qt.AspectRatioMode.KeepAspectRatio,
                            Qt.TransformationMode.SmoothTransformation))
        except:
            pass

    def _preview_video(self):
        """预览视频"""
        import subprocess
        os.startfile(self.video_path)

    def _save_video(self):
        """另存为视频"""
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
            # 左键预览
            self._preview_video()
        elif event.button() == Qt.MouseButton.RightButton:
            # 右键显示菜单
            menu = QMenu(self)
            menu.setStyleSheet("""
                QMenu {
                    background-color: #1a1a2e;
                    color: #ffffff;
                    font-size: 18px;
                    border: 1px solid #2a2a4a;
                    border-radius: 8px;
                    padding: 8px;
                }
                QMenu::item {
                    padding: 10px 30px;
                    border-radius: 6px;
                }
                QMenu::item:selected {
                    background-color: #0f3460;
                }
            """)
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
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(20)

        monitors = RecordController.get_monitors()
        for i, m in enumerate(monitors):
            cb = QCheckBox("显示器 {} ({}x{})".format(i+1, m['width'], m['height']))
            cb.setChecked(i == 0)
            cb.setMinimumHeight(45)
            cb.setStyleSheet("""
                QCheckBox { color: #ffffff; font-size: 22px; spacing: 18px; }
                QCheckBox::indicator { width: 32px; height: 32px; border-radius: 10px;
                    border: 2px solid #2a2a4a; background-color: #16213e; }
                QCheckBox::indicator:checked { background-color: #00d9ff; border-color: #00d9ff; }
                QCheckBox::indicator:hover { border-color: #00d9ff; }
            """)
            layout.addWidget(cb)
            self.checkboxes.append(cb)

        hint = QLabel("可勾选多个显示器同时录制")
        hint.setStyleSheet("color: #808080; font-size: 20px; margin-top: 12px;")
        layout.addWidget(hint)

        if len(monitors) <= 1:
            self.hide()

    def get_selected(self):
        return [i+1 for i, cb in enumerate(self.checkboxes) if cb.isChecked()]

    def setEnabled(self, enabled):
        for cb in self.checkboxes:
            cb.setEnabled(enabled)


class MainWindow(QMainWindow):
    """主窗口"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("录屏王")  # 改名

        # 恢复之前的大窗口尺寸，拉长20%
        self.setMinimumSize(670, 1260)
        self.resize(670, 1260)

        # 初始化录制器
        self.recorder = RecordController()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self._drag_pos = None

        # 使用用户视频目录保存录制文件
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
        layout.setContentsMargins(18, 18, 18, 18)

        card = QFrame()
        card.setObjectName("mainCard")
        layout.addWidget(card)

        cl = QVBoxLayout(card)
        cl.setContentsMargins(0, 0, 0, 0)

        # 标题栏 - 改名
        title = TitleBar("录屏王")
        title.close_clicked.connect(self._on_close)
        title.minimize_clicked.connect(self.showMinimized)
        cl.addWidget(title)

        # 内容区域
        content = QWidget()
        ct = QVBoxLayout(content)
        ct.setContentsMargins(30, 25, 30, 25)
        ct.setSpacing(18)  # 增加间距

        # 状态区
        sframe = QFrame()
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
        self.info_frame.setStyleSheet("background: #16213e; border-radius: 10px;")
        info_layout = QVBoxLayout(self.info_frame)
        info_layout.setContentsMargins(18, 14, 18, 14)
        self.info_label = QLabel("选择录制模式后点击开始")
        self.info_label.setStyleSheet("color: #a0a0a0; font-size: 22px;")
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_layout.addWidget(self.info_label)
        ct.addWidget(self.info_frame)

        ct.addWidget(self._line())

        # 模式选择
        ct.addWidget(self._label("录制模式"))
        ml = QHBoxLayout()
        ml.setSpacing(18)

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

        # 控制按钮 - 三个按钮放在同一行
        ct.addSpacing(12)

        bl = QHBoxLayout()
        bl.setSpacing(20)

        self.pause_btn = QPushButton("⏸  暂停")
        self.pause_btn.setEnabled(False)
        self.pause_btn.clicked.connect(self._toggle_pause)
        self.pause_btn.setFixedHeight(70)
        bl.addWidget(self.pause_btn)

        self.record_btn = RecordButton()
        self.record_btn.clicked.connect(self._toggle_record)
        bl.addWidget(self.record_btn)

        self.stop_btn = QPushButton("⏹  停止")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._stop_record)
        self.stop_btn.setFixedHeight(70)
        bl.addWidget(self.stop_btn)

        ct.addLayout(bl)

        ct.addWidget(self._line())

        # 视频列表
        ct.addWidget(self._label("已录制视频（点击另存为）"))

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFixedHeight(150)  # 调整高度
        scroll.setStyleSheet("""
            QScrollArea { background: transparent; border: 1px solid #2a2a4a; border-radius: 12px; }
            QScrollBar:horizontal { height: 10px; background: #16213e; border-radius: 5px; }
            QScrollBar::handle:horizontal { background: #e94560; border-radius: 5px; }
        """)

        self.video_container = QWidget()
        self.video_layout = QHBoxLayout(self.video_container)
        self.video_layout.setContentsMargins(12, 12, 12, 12)
        self.video_layout.setSpacing(12)
        self.video_layout.addStretch()
        scroll.setWidget(self.video_container)
        ct.addWidget(scroll)

        # 底部提示
        hint = QLabel("F9 开始/停止  |  F10 暂停/继续  |  ESC 退出")
        hint.setStyleSheet("color: #808080; font-size: 20px;")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ct.addWidget(hint)

        cl.addWidget(content)
        self._apply_styles()

    def _label(self, text):
        l = QLabel(text)
        l.setStyleSheet("color: #a0a0a0; font-size: 22px; font-weight: bold;")
        return l

    def _line(self):
        l = QFrame()
        l.setFixedHeight(1)
        l.setStyleSheet("background-color: #2a2a4a;")
        return l

    def _apply_styles(self):
        self.setStyleSheet("""
            #centralWidget { background: transparent; }
            #mainCard { background-color: #1a1a2e; border-radius: 16px; border: 1px solid #2a2a4a; }
            #statusLabel { color: #00d9ff; font-size: 30px; font-weight: bold; margin-left: 12px; }
            QPushButton { background-color: #0f3460; color: #ffffff; border: none; border-radius: 12px;
                padding: 14px 30px; font-size: 24px; font-weight: bold; }
            QPushButton:hover { background-color: #1a4a80; }
            QPushButton:disabled { background-color: #2a2a4a; color: #5a5a7a; }
            QToolTip { font-size: 20px; padding: 6px 10px; border-radius: 6px; }
            QMessageBox { font-size: 20px; }
        """)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if self._drag_pos:
            self.move(event.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None

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
            "color: {}; font-size: 17px; font-weight: bold; margin-left: 12px;".format(
                colors.get(status, "#ffffff")))

    def _on_status(self, status):
        pass

    def _on_complete(self, path):
        if os.path.exists(path):
            card = VideoCard(path)
            self.video_layout.insertWidget(0, card)

    def _on_close(self):
        """标题栏关闭按钮"""
        self.close()

    def closeEvent(self, event):
        """拦截系统关闭事件（Alt+F4、任务栏关闭等）"""
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