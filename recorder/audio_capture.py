# -*- coding: utf-8 -*-
"""
音频采集模块 - 录制麦克风 + 系统声音 (WASAPI Loopback)

依赖: PyAudioWPatch (pip install PyAudioWPatch)
可选: av (pip install av) 用于音视频合并
"""

import os
import threading
import time
import wave
import numpy as np
import subprocess
try:
    import pyaudiowpatch as pyaudio
    HAS_AUDIO = True
except ImportError:
    HAS_AUDIO = False


class AudioCapture:
    """录制麦克风和系统声音并实时混音输出为 WAV"""

    def __init__(self, output_path, record_mic=True, record_system=True):
        self.output_path = output_path
        self.record_mic = record_mic and HAS_AUDIO
        self.record_system = record_system and HAS_AUDIO

        # 始终输出立体声
        self._out_channels = 2
        self._out_rate = 44100  # 会被更新为系统音频采样率

        self._pa = None
        self._mic_stream = None
        self._sys_stream = None
        self._mic_rate = 44100
        self._mic_channels = 1
        self._sys_rate = 44100
        self._sys_channels = 2

        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._thread = None
        self._wav_file = None

        # 运行时静音控制 (用户可在录制中切换)
        self.mic_muted = False
        self.sys_muted = False

    def start(self):
        if not HAS_AUDIO:
            return False
        if not self.record_mic and not self.record_system:
            return False

        try:
            self._pa = pyaudio.PyAudio()

            if self.record_system:
                self._open_loopback()
            if self.record_mic:
                self._open_mic()

            if not self._mic_stream and not self._sys_stream:
                self._cleanup_pa()
                return False

            # 使用系统音频采样率作为输出速率 (音质更好)
            if self._sys_stream:
                self._out_rate = self._sys_rate
            elif self._mic_stream:
                self._out_rate = self._mic_rate

            self._wav_file = wave.open(self.output_path, 'wb')
            self._wav_file.setnchannels(self._out_channels)
            self._wav_file.setsampwidth(2)
            self._wav_file.setframerate(self._out_rate)

            self._thread = threading.Thread(target=self._worker, daemon=True)
            self._thread.start()
            return True

        except Exception as e:
            print(f"[AudioCapture] 启动失败: {e}")
            self._cleanup_pa()
            return False

    def _open_loopback(self):
        """打开 WASAPI Loopback 设备 (系统声音)"""
        try:
            wasapi_info = self._pa.get_host_api_info_by_type(pyaudio.paWASAPI)
            default_speakers = self._pa.get_device_info_by_index(
                wasapi_info["defaultOutputDevice"])

            loopback = None
            if default_speakers.get("isLoopbackDevice"):
                loopback = default_speakers
            else:
                for dev in self._pa.get_loopback_device_info_generator():
                    if default_speakers["name"] in dev["name"]:
                        loopback = dev
                        break

            if not loopback:
                print("[AudioCapture] 未找到 WASAPI Loopback 设备")
                return

            self._sys_channels = min(loopback["maxInputChannels"], self._out_channels)
            self._sys_rate = int(loopback["defaultSampleRate"])
            chunk = int(self._sys_rate * 0.02)

            self._sys_stream = self._pa.open(
                format=pyaudio.paInt16,
                channels=self._sys_channels,
                rate=self._sys_rate,
                input=True,
                input_device_index=loopback["index"],
                frames_per_buffer=chunk
            )
            print(f"[AudioCapture] 系统音频已开启: {self._sys_rate}Hz {self._sys_channels}ch")

        except Exception as e:
            print(f"[AudioCapture] 系统音频打开失败: {e}")
            self._sys_stream = None

    def _open_mic(self):
        """打开默认麦克风"""
        try:
            info = self._pa.get_default_input_device_info()
            self._mic_channels = min(info['maxInputChannels'], self._out_channels)
            self._mic_rate = int(info['defaultSampleRate'])
            chunk = int(self._mic_rate * 0.02)

            self._mic_stream = self._pa.open(
                format=pyaudio.paInt16,
                channels=self._mic_channels,
                rate=self._mic_rate,
                input=True,
                frames_per_buffer=chunk
            )
            print(f"[AudioCapture] 麦克风已开启: {self._mic_rate}Hz {self._mic_channels}ch")

        except Exception as e:
            print(f"[AudioCapture] 麦克风打开失败: {e}")
            self._mic_stream = None

    def _worker(self):
        """采集 + 混音主循环"""
        mic_chunk = int(self._mic_rate * 0.02) if self._mic_stream else 0
        sys_chunk = int(self._sys_rate * 0.02) if self._sys_stream else 0

        while not self._stop_event.is_set():
            if self._pause_event.is_set():
                self._drain(mic_chunk, sys_chunk)
                time.sleep(0.01)
                continue

            mic_data = None
            sys_data = None

            if self._mic_stream:
                try:
                    raw = self._mic_stream.read(mic_chunk, exception_on_overflow=False)
                    if not self.mic_muted:
                        mic_data = raw
                except:
                    pass

            if self._sys_stream:
                try:
                    raw = self._sys_stream.read(sys_chunk, exception_on_overflow=False)
                    if not self.sys_muted:
                        sys_data = raw
                except:
                    pass

            mixed = self._normalize_and_mix(mic_data, sys_data)
            if mixed and self._wav_file:
                try:
                    self._wav_file.writeframes(mixed)
                except:
                    pass

    def _drain(self, mic_chunk, sys_chunk):
        """暂停期间排空缓冲区 (防溢出)"""
        if self._mic_stream:
            try:
                self._mic_stream.read(mic_chunk, exception_on_overflow=False)
            except:
                pass
        if self._sys_stream:
            try:
                self._sys_stream.read(sys_chunk, exception_on_overflow=False)
            except:
                pass

    def _normalize_and_mix(self, mic_data, sys_data):
        """重采样 → 立体声 → 混音"""
        chunks = []
        for data, rate, ch in [
            (mic_data, self._mic_rate, self._mic_channels),
            (sys_data, self._sys_rate, self._sys_channels),
        ]:
            if not data:
                continue
            arr = np.frombuffer(data, dtype=np.int16)
            arr = self._to_stereo(arr, ch)
            arr = self._resample(arr, rate, self._out_rate)
            chunks.append(arr)

        if not chunks:
            return None
        if len(chunks) == 1:
            return chunks[0].tobytes()

        min_len = min(len(c) for c in chunks)
        mixed = np.clip(
            chunks[0][:min_len].astype(np.int32) + chunks[1][:min_len].astype(np.int32),
            -32768, 32767
        ).astype(np.int16)
        return mixed.tobytes()

    def _to_stereo(self, arr, channels):
        if channels == 2:
            return arr
        if channels == 1:
            return np.column_stack([arr, arr]).flatten()
        return arr.reshape(-1, channels)[:, :2].flatten()

    def _resample(self, arr, orig_rate, target_rate):
        if orig_rate == target_rate:
            return arr
        ratio = target_rate / orig_rate
        if self._out_channels == 2:
            left = arr[0::2].astype(np.float64)
            right = arr[1::2].astype(np.float64)
            n = int(len(left) * ratio)
            if n == 0:
                return arr
            idx = np.linspace(0, len(left) - 1, n)
            l = np.interp(idx, np.arange(len(left)), left).astype(np.int16)
            r = np.interp(idx, np.arange(len(right)), right).astype(np.int16)
            return np.column_stack([l, r]).flatten()
        else:
            n = int(len(arr) * ratio)
            if n == 0:
                return arr
            idx = np.linspace(0, len(arr) - 1, n)
            return np.interp(idx, np.arange(len(arr)), arr.astype(np.float64)).astype(np.int16)

    def pause(self):
        self._pause_event.set()

    def resume(self):
        self._pause_event.clear()

    def stop(self):
        """停止采集并关闭 WAV 文件"""
        self._stop_event.set()
        self._pause_event.clear()

        if self._thread:
            self._thread.join(timeout=3.0)

        if self._wav_file:
            try:
                self._wav_file.close()
            except:
                pass
            self._wav_file = None

        self._cleanup_pa()

        if self.output_path and os.path.exists(self.output_path) and os.path.getsize(self.output_path) > 44:
            return self.output_path
        return None

    def _cleanup_pa(self):
        for stream in (self._mic_stream, self._sys_stream):
            if stream:
                try:
                    stream.stop_stream()
                    stream.close()
                except:
                    pass
        self._mic_stream = None
        self._sys_stream = None
        if self._pa:
            try:
                self._pa.terminate()
            except:
                pass
            self._pa = None

    @staticmethod
    def is_available():
        return HAS_AUDIO


def merge_audio_video(video_path, audio_path, output_path):
    """使用 FFmpeg 将音频和视频合并 (瞬间完成且绝对稳定)"""
    if not os.path.exists(video_path) or not os.path.exists(audio_path):
        return video_path

    try:
        # 构建 FFmpeg 命令
        # -c:v copy: 视频流直接拷贝，免去漫长渲染，瞬间完成
        # -c:a aac: 将 WAV 音频压缩为标准 AAC 格式
        cmd = [
            'ffmpeg', '-y',
            '-i', video_path,
            '-i', audio_path,
            '-c:v', 'copy',
            '-c:a', 'aac',
            output_path
        ]

        # 隐藏控制台黑窗口 (针对 Windows 系统)
        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        print(f"[合并中] 正在将音频混入视频: {output_path}")

        # 执行命令，最多等待 30 秒
        result = subprocess.run(
            cmd,
            startupinfo=startupinfo,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30
        )

        # 检查是否合并成功
        if result.returncode == 0 and os.path.exists(output_path):
            print("[合并成功] 音视频已完美融合！")
            return output_path
        else:
            print(f"[合并失败] FFmpeg 返回码: {result.returncode}")
            # 打印出 FFmpeg 的报错信息方便排查
            print(result.stderr.decode('utf-8', errors='ignore'))
            return video_path

    except FileNotFoundError:
        print("\n[致命错误] 系统未安装 FFmpeg！")
        print("请下载 FFmpeg.exe 并配置到系统环境变量，或放入项目根目录中。")
        return video_path
    except Exception as e:
        print(f"[合并异常] 发生未知错误: {e}")
        return video_path
