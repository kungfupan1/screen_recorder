# -*- coding: utf-8 -*-
"""
录屏王 - 主程序入口
"""
import sys
import os
import ctypes

# DPI 设置：强制 Windows 不缩放
if sys.platform == "win32":
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "0"
os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "0"

# 注意：不再手动设置 QT_QPA_PLATFORM_PLUGIN_PATH
# PyInstaller 的 pyi_rth_pyside6 hook 会自动处理插件路径

# 获取程序目录
if getattr(sys, 'frozen', False):
    APP_DIR = os.path.dirname(sys.executable)
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, APP_DIR)

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont
from ui.main_window import MainWindow

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("录屏王")
    app.setApplicationVersion("1.0.0")
    font = QFont("Microsoft YaHei", 20)
    app.setFont(font)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()