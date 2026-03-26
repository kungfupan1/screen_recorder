# -*- coding: utf-8 -*-
"""
录屏大师 - 主程序入口
修复了 Qt 插件找不到的问题，并引入了底层 DPI 绝对物理坐标系感知
"""
import sys
import os
import ctypes

# ===== 1. 终极 DPI 解决方案：强制 Windows 不缩放我们的程序 =====
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

# ===== 2. 核弹级修复：强制指定平台插件物理路径 =====
import PySide6
# 动态获取当前 PySide6 安装的绝对真实路径
pyside_dir = os.path.dirname(PySide6.__file__)
# 精准定位到 platforms 文件夹 (qwindows.dll 所在位置)
platform_plugin_path = os.path.join(pyside_dir, 'plugins', 'platforms')
# 强制写入系统环境变量
os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = platform_plugin_path

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