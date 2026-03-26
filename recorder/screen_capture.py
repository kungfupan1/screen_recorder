"""
屏幕捕获模块 - 使用mss进行高性能屏幕捕获
"""
import mss
import numpy as np
from typing import Optional, Tuple
from threading import Event


class ScreenCapture:
    """高性能屏幕捕获类"""

    def __init__(self):
        self.sct = mss.mss()
        self.monitors = self.sct.monitors
        self._stop_event = Event()

    def get_monitor_info(self, monitor_index: int = 1) -> dict:
        """获取显示器信息

        Args:
            monitor_index: 显示器索引，1为主显示器

        Returns:
            显示器信息字典
        """
        if monitor_index < 1 or monitor_index >= len(self.monitors):
            monitor_index = 1
        return self.monitors[monitor_index]

    def get_all_monitors(self) -> list:
        """获取所有显示器信息"""
        return self.monitors[1:]  # 第一个是虚拟的全屏组合

    def capture_fullscreen(self, monitor_index: int = 1) -> np.ndarray:
        """捕获全屏

        Args:
            monitor_index: 显示器索引

        Returns:
            numpy数组格式的图像 (BGR)
        """
        monitor = self.get_monitor_info(monitor_index)
        screenshot = self.sct.grab(monitor)
        # 转换为numpy数组并从BGRA转为BGR
        img = np.array(screenshot)
        return img[:, :, :3]  # 去掉alpha通道

    def capture_region(self, x: int, y: int, width: int, height: int) -> np.ndarray:
        """捕获指定区域

        Args:
            x: 起始X坐标
            y: 起始Y坐标
            width: 宽度
            height: 高度

        Returns:
            numpy数组格式的图像 (BGR)
        """
        region = {
            "left": x,
            "top": y,
            "width": width,
            "height": height
        }
        screenshot = self.sct.grab(region)
        img = np.array(screenshot)
        return img[:, :, :3]

    def get_screen_size(self, monitor_index: int = 1) -> Tuple[int, int]:
        """获取屏幕尺寸

        Args:
            monitor_index: 显示器索引

        Returns:
            (宽度, 高度) 元组
        """
        monitor = self.get_monitor_info(monitor_index)
        return monitor["width"], monitor["height"]

    def stop(self):
        """停止捕获"""
        self._stop_event.set()

    def reset(self):
        """重置停止事件"""
        self._stop_event.clear()

    def close(self):
        """关闭资源"""
        self.sct.close()