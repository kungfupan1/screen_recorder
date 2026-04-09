# -*- coding: utf-8 -*-
"""
音频处理器 - 可插拔处理器链

继承 AudioProcessor 并重写 process() 来添加音效。
处理器在 Python 写入线程中执行，不影响采集时钟。
"""

import numpy as np


class AudioProcessor:
    """处理器基类"""

    def process(self, data: bytes, rate: int, channels: int) -> bytes:
        """处理一帧音频数据

        Args:
            data: PCM int16 原始字节
            rate: 采样率
            channels: 声道数
        Returns:
            处理后的 PCM 字节
        """
        return data


class VolumeProcessor(AudioProcessor):
    """音量调节"""

    def __init__(self, gain: float = 1.0):
        """
        Args:
            gain: 增益倍数 (1.0=原音量, 2.0=两倍, 0.5=一半)
        """
        self.gain = gain

    def process(self, data: bytes, rate: int, channels: int) -> bytes:
        arr = np.frombuffer(data, dtype=np.int16).astype(np.float32)
        arr = np.clip(arr * self.gain, -32768, 32767).astype(np.int16)
        return arr.tobytes()
