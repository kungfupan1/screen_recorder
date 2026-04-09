# -*- coding: utf-8 -*-
"""
音频录制模块 - 多轨独立录制 + 回调采集

Architecture:
  AudioTrack (独立音轨) x N  →  merge_tracks (ffmpeg 合并)

Usage:
    from recorder.audio import AudioCapture, merge_tracks
"""

import os
import threading
from datetime import datetime

try:
    import pyaudiowpatch as pyaudio
    HAS_AUDIO = True
except ImportError:
    HAS_AUDIO = False

from recorder.audio.track import AudioTrack
from recorder.audio.sources import find_mic_device, find_loopback_device
from recorder.audio.processors import AudioProcessor, VolumeProcessor
from recorder.audio.mixer import merge_tracks


class AudioCapture:
    """门面类 - 管理多条独立音轨，保持与 controller.py 的兼容接口"""

    def __init__(self, output_dir, record_mic=True, record_system=True):
        self.output_dir = output_dir
        self._tracks = {}
        self._pa = None

        if not HAS_AUDIO:
            return

        try:
            self._pa = pyaudio.PyAudio()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            if record_system:
                dev = find_loopback_device(self._pa)
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
                dev = find_mic_device(self._pa)
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
            failed = []
            for name, track in self._tracks.items():
                if not track.start(self._pa):
                    failed.append(name)

            for name in failed:
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

        if self._pa:
            try:
                self._pa.terminate()
            except:
                pass
            self._pa = None

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
