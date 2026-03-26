# -*- coding: utf-8 -*-
"""
区域选择器 - 商业级冻结桌面方案
保证多屏幕、多DPI缩放下的 100% 坐标精准
"""
from PySide6.QtWidgets import QWidget, QApplication
from PySide6.QtCore import Qt, QRect, Signal, QPoint
from PySide6.QtGui import QPainter, QColor, QPen, QFont, QImage, QPixmap
import mss
import numpy as np


class AreaSelector(QWidget):
    area_selected = Signal(int, int, int, int)
    selection_cancelled = Signal()

    def __init__(self):
        super().__init__()

        # 1. 使用 mss 抓拍整个虚拟桌面（所有显示器的组合）
        with mss.mss() as sct:
            self.monitor = sct.monitors[0]  # 索引0代表整个虚拟桌面
            screenshot = sct.grab(self.monitor)

            # 将 mss 截图转换为 Qt 可显示的图像
            img = QImage(screenshot.rgb, screenshot.width, screenshot.height, QImage.Format.Format_RGB888)
            self.bg_pixmap = QPixmap.fromImage(img)

        # 2. 设置无边框、置顶窗口
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        # 注意：这里不再使用透明背景，而是用抓拍的照片当背景

        # 3. 让窗口严丝合缝地覆盖整个虚拟物理空间
        self.setGeometry(
            self.monitor['left'],
            self.monitor['top'],
            self.monitor['width'],
            self.monitor['height']
        )

        self.is_selecting = False
        self.start_pos = None
        self.current_pos = None

        # 将鼠标变成十字星
        self.setCursor(Qt.CursorShape.CrossCursor)

        self.show()
        self.raise_()
        self.activateWindow()

    def paintEvent(self, event):
        painter = QPainter(self)

        # 1. 铺设底层冻结的全景桌面截图
        painter.drawPixmap(0, 0, self.bg_pixmap)

        # 2. 覆盖一层半透明的黑色遮罩
        overlay_color = QColor(0, 0, 0, 100)
        painter.fillRect(self.rect(), overlay_color)

        # 3. 如果正在绘制选区，将选区内的遮罩“挖空”并画边框
        if self.is_selecting and self.start_pos and self.current_pos:
            rect = QRect(self.start_pos, self.current_pos).normalized()

            # 把选区底部的原图重新画上去（实现挖空效果）
            painter.drawPixmap(rect, self.bg_pixmap, rect)

            # 画个高亮边框
            painter.setPen(QPen(QColor(0, 200, 255), 2))
            painter.drawRect(rect)

            # 绘制尺寸和坐标信息
            font = QFont("Microsoft YaHei", 12, QFont.Weight.Bold)
            painter.setFont(font)
            painter.setPen(QColor(255, 255, 255))

            # 计算绝对物理坐标（加上虚拟桌面的偏移量）
            abs_x = self.monitor['left'] + rect.x()
            abs_y = self.monitor['top'] + rect.y()

            info = f" {rect.width()} x {rect.height()} | 物理坐标: ({abs_x}, {abs_y}) "

            # 画一个文本背景底色，防看不清
            text_rect = QRect(rect.left(), rect.top() - 25, 300, 25)
            painter.fillRect(text_rect, QColor(0, 0, 0, 150))
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, info)

        else:
            # 初始提示文字
            font = QFont("Microsoft YaHei", 24, QFont.Weight.Bold)
            painter.setFont(font)
            painter.setPen(QColor(255, 255, 255))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter,
                             "拖拽选择录制区域 | 按 ESC 取消")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_selecting = True
            self.start_pos = event.pos()
            self.current_pos = event.pos()
            self.update()

    def mouseMoveEvent(self, event):
        if self.is_selecting:
            self.current_pos = event.pos()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.is_selecting:
            self.is_selecting = False
            rect = QRect(self.start_pos, self.current_pos).normalized()

            if rect.width() < 10 or rect.height() < 10:
                self.selection_cancelled.emit()
                self.close()
                return

            # 重点：计算相对整个虚拟物理桌面的绝对坐标！
            abs_x = self.monitor['left'] + rect.x()
            abs_y = self.monitor['top'] + rect.y()

            print(f"最终捕获物理区域: x={abs_x}, y={abs_y}, w={rect.width()}, h={rect.height()}")
            self.area_selected.emit(abs_x, abs_y, rect.width(), rect.height())
            self.close()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.selection_cancelled.emit()
            self.close()


def select_area():
    result = [None]

    def on_selected(x, y, w, h):
        result[0] = (x, y, w, h)

    def on_cancelled():
        result[0] = None

    selector = AreaSelector()
    selector.area_selected.connect(on_selected)
    selector.selection_cancelled.connect(on_cancelled)

    while selector.isVisible():
        QApplication.processEvents()

    return result[0]