# -*- coding: utf-8 -*-
"""
音频录制模块 - 多轨独立录制 + 回调采集

Architecture:
  AudioTrack (独立音轨) x N  →  merge_tracks (ffmpeg 合并)

Usage:
    from recorder.audio import AudioCapture, merge_tracks
"""

import os
import atexit
import threading
from datetime import datetime

try:
    import pyaudiowpatch as pyaudio
    HAS_AUDIO = True
except ImportError:
    HAS_AUDIO = False

from recorder.audio.track import AudioTrack
from recorder.audio.sources import get_cached_devices, refresh_device_cache
from recorder.audio.processors import AudioProcessor, VolumeProcessor
from recorder.audio.mixer import merge_tracks

# ──────────── 模块级 PyAudio 缓存 ────────────
_cached_pa = None


def _cleanup_pa():
    """程序退出时清理缓存的 PyAudio 实例"""
    global _cached_pa
    if _cached_pa:
        try:
            _cached_pa.terminate()
        except:
            pass
        _cached_pa = None


atexit.register(_cleanup_pa)


def preinit_audio():
    """预初始化音频子系统（在后台线程调用，提前完成 WASAPI 设备探测）

    首次调用会执行 PyAudio() + 设备枚举（约 300-500ms），
    后续录制直接复用缓存，无需再等。
    """
    global _cached_pa
    if not HAS_AUDIO or _cached_pa is not None:
        return
    try:
        _cached_pa = pyaudio.PyAudio()
        get_cached_devices(_cached_pa)
        print("[AudioCapture] 预初始化完成")
    except Exception as e:
        print(f"[AudioCapture] 预初始化失败: {e}")
        if _cached_pa:
            try:
                _cached_pa.terminate()
            except:
                pass
            _cached_pa = None


class AudioCapture:
    """门面类 - 管理多条独立音轨，保持与 controller.py 的兼容接口"""

    def __init__(self, output_dir, record_mic=True, record_system=True):
        global _cached_pa

        self.output_dir = output_dir
        self._tracks = {}
        self._pa = None

        if not HAS_AUDIO:
            return

        try:
            # 复用缓存的 PyAudio 实例，避免每次录制重新初始化 PortAudio
            if _cached_pa is not None:
                self._pa = _cached_pa
            else:
                self._pa = pyaudio.PyAudio()
                _cached_pa = self._pa

            # 获取设备信息（首次探测后缓存）
            devices = get_cached_devices(self._pa)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            if record_system:
                dev = devices.get('sys')
                if dev:
                    path = os.path.join(output_dir, f"audio_sys_{timestamp}.wav")
                    self._tracks['sys'] = AudioTrack(
                        name='sys',
                        device_index=dev['index'],
                        sample_rate=dev['sample_rate'],
                        channels=dev['channels'],
                        output_path=path
                    )

            if record_mic:
                dev = devices.get('mic')
                if dev:
                    path = os.path.join(output_dir, f"audio_mic_{timestamp}.wav")
                    self._tracks['mic'] = AudioTrack(
                        name='mic',
                        device_index=dev['index'],
                        sample_rate=dev['sample_rate'],
                        channels=dev['channels'],
                        output_path=path
                    )

        except Exception as e:
            print(f"[AudioCapture] 初始化失败: {e}")

    def start(self):
        if not self._pa or not self._tracks:
            return False

        try:
            # 并行打开所有音轨流（两条 pa.open() 同时执行，省一半时间）
            results = {}

            def _open_track(name, track):
                try:
                    results[name] = track.start(self._pa)
                except Exception as e:
                    print(f"[AudioCapture] {name} 启动异常: {e}")
                    results[name] = False

            threads = []
            for name, track in self._tracks.items():
                t = threading.Thread(target=_open_track, args=(name, track))
                t.start()
                threads.append(t)

            for t in threads:
                t.join()

            # 移除失败的音轨
            failed = [name for name, ok in results.items() if not ok]
            if failed:
                # 音轨打开失败，可能是设备缓存过期，刷新后重试一次
                refresh_device_cache(self._pa)
                devices = get_cached_devices(self._pa)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                retry_ok = []
                for name in failed:
                    dev = devices.get(name)
                    if not dev:
                        self._tracks.pop(name, None)
                        continue
                    path = os.path.join(self.output_dir, f"audio_{name}_{timestamp}.wav")
                    new_track = AudioTrack(
                        name=name,
                        device_index=dev['index'],
                        sample_rate=dev['sample_rate'],
                        channels=dev['channels'],
                        output_path=path
                    )
                    if new_track.start(self._pa):
                        self._tracks[name] = new_track
                        retry_ok.append(name)
                    else:
                        self._tracks.pop(name, None)

            if not self._tracks:
                return False

            print(f"[AudioCapture] 已启动 {len(self._tracks)} 条音轨: {list(self._tracks.keys())}")
            return True

        except Exception as e:
            print(f"[AudioCapture] 启动失败: {e}")
            return False

    def stop(self):
        """停止所有音轨

        Returns:
            dict: {"mic": "path/to/mic.wav", "sys": "path/to/sys.wav"}
        """
        results = {}
        for name, track in self._tracks.items():
            path = track.stop()
            if path:
                results[name] = path

        # 不销毁 PyAudio 实例，保持缓存供下次录制复用
        return results

    def pause(self):
        for track in self._tracks.values():
            track.pause()

    def resume(self):
        for track in self._tracks.values():
            track.resume()

    def get_track(self, track_name):
        """获取指定音轨 (用于添加处理器等高级操作)"""
        return self._tracks.get(track_name)

    def set_mute(self, track_name, muted):
        """设置指定音轨静音"""
        track = self._tracks.get(track_name)
        if track:
            track.muted = muted

    @staticmethod
    def is_available():
        return HAS_AUDIO
