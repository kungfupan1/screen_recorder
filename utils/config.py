# -*- coding: utf-8 -*-
"""
配置管理
"""
import os
import sys


def get_app_dir():
    """获取应用目录，支持打包后的路径"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_resource_path(relative_path):
    """获取资源文件路径，支持PyInstaller打包"""
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = get_app_dir()
    return os.path.join(base_path, relative_path)


# 默认配置
DEFAULT_CONFIG = {
    "fps": 30,
    "output_dir": "recordings",
    "format": "mp4",
}


class Config:
    """配置类"""

    def __init__(self):
        self.fps = DEFAULT_CONFIG["fps"]
        self.output_dir = os.path.join(get_app_dir(), DEFAULT_CONFIG["output_dir"])

        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)