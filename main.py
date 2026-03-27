# -*- coding: utf-8 -*-
"""
录屏王 - 主程序入口
极简纯净版，完全信任 PyInstaller 的默认机制
"""
import sys
import os
import ctypes

# 1. 强制 Windows 物理 DPI
if sys.platform == "win32":
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        pass
os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "0"
os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "0"

# 2. 纯粹的模块路径声明（绝不手动干预 DLL）
if getattr(sys, 'frozen', False):
    APP_DIR = os.path.dirname(sys.executable)
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))

if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont
from ui.main_window import MainWindow

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("录屏王")
    app.setApplicationVersion("1.0.0")
    font = QFont("Microsoft YaHei", 16)
    app.setFont(font)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()