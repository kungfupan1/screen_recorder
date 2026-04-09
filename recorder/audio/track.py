# -*- coding: utf-8 -*-
"""
AudioTrack - 独立音轨 (回调采集 + 队列 + 写入线程 + 处理器链)

线程模型:
  C 线程 (声卡硬件时钟) → Queue → Python 线程 (处理器链 + 写 WAV)
"""

import os
import threading
import time
import wave
from queue import Queue, Full, Empty

try:
    import pyaudiowpatch as pyaudio
    HAS_AUDIO = True
except ImportError:
    HAS_AUDIO = False


class AudioTrack:
    """一条完全独立的音频录制轨道"""

    def __init__(self, name, device_index, sample_rate, channels,
                 output_path, processors=None):
        """
        Args:
            name: 轨道名称 (如 "mic", "sys")
            device_index: PyAudio 设备索引
            sample_rate: 采样率
            channels: 声道数 (1=mono, 2=stereo)
            output_path: WAV 输出路径
            processors: AudioProcessor 列表 (可选)
        """
        self.name = name
        self.device_index = device_index
        self.sample_rate = sample_rate
        self.channels = channels
        self.output_path = output_path
        self.processors = list(processors) if processors else []

        # 内部状态
        self._queue = Queue(maxsize=100)  # ~2 秒缓冲
        self._stream = None
        self._writer_thread = None
        self._wav_file = None
        self._pa = None

        # 线程安全标志
        self._stop_event = threading.Event()
        self._paused_event = threading.Event()
        self._muted_event = threading.Event()

        # 统计
        self._dropped_frames = 0
        self._silence_filled = 0  # 静音填充帧数统计

    # ──────────── 公开接口 ────────────

    @property
    def muted(self):
        return self._muted_event.is_set()

    @muted.setter
    def muted(self, value):
        if value:
            self._muted_event.set()
        else:
            self._muted_event.clear()

    def add_processor(self, processor):
        """添加处理器到链尾"""
        self.processors.append(processor)

    def remove_processor(self, processor):
        """移除指定处理器"""
        if processor in self.processors:
            self.processors.remove(processor)

    def start(self, pa):
        """启动音轨 (回调模式)

        Args:
            pa: PyAudio 实例 (共享，由调用方管理生命周期)
        Returns:
            bool: 是否启动成功
        """
        if not HAS_AUDIO:
            return False

        self._pa = pa
        self._stop_event.clear()
        self._dropped_frames = 0

        chunk = int(self.sample_rate * 0.02)  # 20ms per chunk

        try:
            self._wav_file = wave.open(self.output_path, 'wb')
            self._wav_file.setnchannels(self.channels)
            self._wav_file.setsampwidth(2)
            self._wav_file.setframerate(self.sample_rate)

            self._stream = pa.open(
                format=pyaudio.paInt16,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                input_device_index=self.device_index,
                frames_per_buffer=chunk,
                stream_callback=self._callback
            )

            self._writer_thread = threading.Thread(
                target=self._writer, daemon=True,
                name=f"AudioTrack-{self.name}"
            )
            self._writer_thread.start()

            print(f"[AudioTrack:{self.name}] 已启动: {self.sample_rate}Hz {self.channels}ch (device {self.device_index})")
            return True

        except Exception as e:
            print(f"[AudioTrack:{self.name}] 启动失败: {e}")
            self._cleanup()
            return False

    def pause(self):
        """暂停 - 停止回调，音视频同步跳过暂停段"""
        self._paused_event.set()
        if self._stream:
            try:
                self._stream.stop_stream()
            except:
                pass

    def resume(self):
        """恢复 - 重启回调"""
        self._paused_event.clear()
        if self._stream:
            try:
                self._stream.start_stream()
            except:
                pass

    def stop(self):
        """停止采集，排空队列，关闭文件

        Returns:
            str: WAV 文件路径，或 None
        """
        self._stop_event.set()
        self._paused_event.clear()

        # 1. 停止流 (停止回调)
        if self._stream:
            try:
                self._stream.stop_stream()
            except:
                pass
            try:
                self._stream.close()
            except:
                pass
            self._stream = None

        # 2. 等待写入线程排空队列并退出
        if self._writer_thread and self._writer_thread.is_alive():
            self._writer_thread.join(timeout=5.0)

        # 3. 兜底: 确保 WAV 关闭
        if self._wav_file:
            try:
                self._wav_file.close()
            except:
                pass
            self._wav_file = None

        if self._dropped_frames > 0:
            print(f"[AudioTrack:{self.name}] 丢帧: {self._dropped_frames}")
        if self._silence_filled > 0:
            secs = self._silence_filled / self.sample_rate
            print(f"[AudioTrack:{self.name}] 静音填充: {self._silence_filled} 帧 ({secs:.1f}s)")

        if self.output_path and os.path.exists(self.output_path) and os.path.getsize(self.output_path) > 44:
            print(f"[AudioTrack:{self.name}] 录制完成: {self.output_path}")
            return self.output_path
        return None

    # ──────────── 内部实现 ────────────

    def _callback(self, in_data, frame_count, time_info, status):
        """C 线程回调 - 只做一件事: 把数据塞进队列，绝不阻塞"""
        try:
            self._queue.put_nowait(in_data)
        except Full:
            self._dropped_frames += 1
        return (None, pyaudio.paContinue)

    def _writer(self):
        """Python 线程 - 基于时间轴推进，从队列取数据，跑处理器链，写 WAV

        核心逻辑：用 time.perf_counter() 跟踪时间轴，确保 WAV 文件时长与实际录制时长一致。
        当回调不触发（如 WASAPI Loopback 无系统声音时），主动填充静音帧。
        """
        bytes_per_sample = self.channels * 2  # int16 = 2 bytes * channels
        start_time = time.perf_counter()
        written_samples = 0  # 已写入的采样数 (per channel)

        while not self._stop_event.is_set() or not self._queue.empty():
            elapsed = time.perf_counter() - start_time
            expected_samples = int(elapsed * self.sample_rate)

            # 时间轴出现空隙 → 填充静音帧
            gap = expected_samples - written_samples
            if gap > 0:
                silence_bytes = gap * bytes_per_sample
                self._write_frame(b'\x00' * silence_bytes)
                written_samples = expected_samples
                self._silence_filled += gap
                continue  # 重新计算，可能还需要继续填充

            # 从队列取数据
            try:
                data = self._queue.get(timeout=0.02)
            except Empty:
                continue

            # 静音: 替换为等长静音帧，保持时轴连续
            if self._muted_event.is_set():
                data = b'\x00' * len(data)

            self._write_frame(data)
            written_samples += len(data) // bytes_per_sample

        # 排空完毕，关闭文件
        if self._wav_file:
            try:
                self._wav_file.close()
            except:
                pass
            self._wav_file = None

    def _write_frame(self, data):
        """处理并写入一帧音频数据"""
        # 处理器链
        for proc in self.processors:
            try:
                data = proc.process(data, self.sample_rate, self.channels)
            except Exception as e:
                print(f"[AudioTrack:{self.name}] 处理器异常: {e}，降级直通")
                break

        if self._wav_file:
            try:
                self._wav_file.writeframes(data)
            except:
                pass

    def _cleanup(self):
        if self._stream:
            try:
                self._stream.close()
            except:
                pass
            self._stream = None
        if self._wav_file:
            try:
                self._wav_file.close()
            except:
                pass
            self._wav_file = None
