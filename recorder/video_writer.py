"""
视频写入模块 - 使用OpenCV进行视频编码
"""
import cv2
import os
from datetime import datetime
from typing import Optional


class VideoWriter:
    """视频写入类，支持H.264编码"""

    def __init__(self, output_dir: str = "recordings"):
        self.output_dir = output_dir
        self.writer: Optional[cv2.VideoWriter] = None
        self.output_path: Optional[str] = None
        self.fps: int = 30
        self.frame_count: int = 0

        # 确保输出目录存在
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

    def start(self, width: int, height: int, fps: int = 30) -> str:
        """开始录制，创建视频文件

        Args:
            width: 视频宽度
            height: 视频高度
            fps: 帧率

        Returns:
            输出文件路径
        """
        self.fps = fps
        self.frame_count = 0

        # 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_path = os.path.join(
            self.output_dir,
            f"recording_{timestamp}.mp4"
        )

        # 使用H.264编码
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')

        # 创建VideoWriter
        self.writer = cv2.VideoWriter(
            self.output_path,
            fourcc,
            fps,
            (width, height)
        )

        if not self.writer.isOpened():
            raise RuntimeError("无法创建视频写入器")

        return self.output_path

    def write_frame(self, frame):
        """写入一帧

        Args:
            frame: BGR格式的numpy数组
        """
        if self.writer is not None:
            self.writer.write(frame)
            self.frame_count += 1

    def stop(self) -> Optional[str]:
        """停止录制

        Returns:
            输出文件路径
        """
        if self.writer is not None:
            self.writer.release()
            self.writer = None

        path = self.output_path
        self.output_path = None
        return path

    def is_recording(self) -> bool:
        """检查是否正在录制"""
        return self.writer is not None and self.writer.isOpened()

    def get_duration(self) -> float:
        """获取已录制时长（秒）"""
        if self.fps > 0:
            return self.frame_count / self.fps
        return 0.0

    def get_frame_count(self) -> int:
        """获取已录制帧数"""
        return self.frame_count