# -*- coding: utf-8 -*-
"""
录制控制器 - 包含完整的控制、暂停/恢复、多屏幕及区域录制支持
"""
import threading
import time
import mss
import cv2
import os
from datetime import datetime
import numpy as np
from queue import Queue, Empty


class ScreenRecorder:
    """单个屏幕录制器"""

    def __init__(self, bounds, output_path, fps=30):
        x, y, w, h = [int(v) for v in bounds]
        self.width = w if w % 2 == 0 else w - 1
        self.height = h if h % 2 == 0 else h - 1
        self.bounds = (x, y, self.width, self.height)

        self.output_path = output_path
        self.fps = fps

        self.writer = None
        self.frame_count = 0
        self.queue = Queue(maxsize=120)
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._capture_thread = None
        self._write_thread = None

    def pause(self):
        """暂停录制"""
        self._pause_event.set()

    def resume(self):
        """恢复录制"""
        self._pause_event.clear()

    def start(self):
        """初始化并开始录制"""
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        self.writer = cv2.VideoWriter(
            self.output_path, fourcc, float(self.fps),
            (self.width, self.height)
        )

        if not self.writer.isOpened():
            raise RuntimeError(f"无法创建视频写入器: {self.output_path}")

        self._capture_thread = threading.Thread(target=self._capture_worker, daemon=True)
        self._capture_thread.start()

        self._write_thread = threading.Thread(target=self._write_worker, daemon=True)
        self._write_thread.start()

        return True

    def _capture_worker(self):
        """捕获线程 - 增加帧率同步与补帧逻辑"""
        with mss.mss() as sct:
            x, y, w, h = self.bounds
            region = {"left": x, "top": y, "width": w, "height": h}

            start_time = time.perf_counter()
            captured_count = 0

            while not self._stop_event.is_set():
                # 响应暂停指令
                if self._pause_event.is_set():
                    pause_start = time.perf_counter()
                    # 暂停期间循环等待
                    while self._pause_event.is_set() and not self._stop_event.is_set():
                        time.sleep(0.1)
                    # 恢复后，扣除暂停的时间，保证时间轴连续
                    start_time += (time.perf_counter() - pause_start)
                    continue

                try:
                    screenshot = sct.grab(region)
                    frame = np.array(screenshot)[:, :, :3]

                    current_time = time.perf_counter()
                    target_count = int((current_time - start_time) * self.fps) + 1

                    frames_to_add = target_count - captured_count
                    for _ in range(frames_to_add):
                        try:
                            self.queue.put_nowait(frame)
                            captured_count += 1
                        except:
                            pass

                except Exception as e:
                    print(f"捕获错误: {e}")

                next_time = start_time + (captured_count / float(self.fps))
                sleep_time = next_time - time.perf_counter()
                if sleep_time > 0:
                    time.sleep(sleep_time)

    def _write_worker(self):
        """写入线程"""
        while not self._stop_event.is_set() or not self.queue.empty():
            try:
                frame = self.queue.get(timeout=0.5)
                if self.writer is not None:
                    self.writer.write(frame)
                    self.frame_count += 1
            except Empty:
                continue

    def stop(self):
        """停止录制"""
        self._stop_event.set()
        self._pause_event.clear()  # 防死锁

        if self._capture_thread and self._capture_thread.is_alive():
            self._capture_thread.join(timeout=2.0)
        if self._write_thread and self._write_thread.is_alive():
            self._write_thread.join(timeout=5.0)

        if self.writer is not None:
            self.writer.release()
            self.writer = None

        return self.frame_count


class RecordController:
    """录制控制器"""

    def __init__(self, output_dir="recordings"):
        self.output_dir = output_dir
        self.is_recording = False
        self.is_paused = False
        self.fps = 30
        self.region = None
        self.selected_monitors = [1]

        self.recorders = []
        self._start_time = 0
        self._paused_duration = 0
        self._pause_start_time = 0

        # 音频控制
        self.record_mic = True
        self.record_system = True
        self._audio_capture = None

        self.on_status_changed = None
        self.on_recording_complete = None

        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

    @staticmethod
    def get_monitors():
        with mss.mss() as sct:
            return sct.monitors[1:]

    def set_monitors(self, indices):
        self.selected_monitors = indices if indices else [1]
        self.region = None

    def set_region(self, x=None, y=None, width=None, height=None):
        if all(v is not None for v in [x, y, width, height]):
            self.region = (int(x), int(y), int(width), int(height))
        else:
            self.region = None

    def set_fullscreen(self):
        self.region = None

    def start(self):
        if self.is_recording:
            return []

        try:
            self.recorders = []
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_paths = []

            with mss.mss() as sct:
                monitors = sct.monitors

                if self.region:
                    output = os.path.join(self.output_dir, f"recording_{timestamp}.mp4")
                    recorder = ScreenRecorder(self.region, output, self.fps)
                    recorder.start()
                    self.recorders.append(recorder)
                    output_paths.append(output)
                else:
                    for mon_idx in self.selected_monitors:
                        if mon_idx >= len(monitors):
                            continue

                        mon = monitors[mon_idx]
                        bounds = (mon["left"], mon["top"], mon["width"], mon["height"])
                        output = os.path.join(self.output_dir, f"recording_screen{mon_idx}_{timestamp}.mp4")

                        recorder = ScreenRecorder(bounds, output, self.fps)
                        recorder.start()
                        self.recorders.append(recorder)
                        output_paths.append(output)

            if not self.recorders:
                raise RuntimeError("没有有效的录制目标")

            # 启动音频采集
            self._audio_capture = None
            if self.record_mic or self.record_system:
                from recorder.audio_capture import AudioCapture
                audio_path = os.path.join(self.output_dir, f"audio_{timestamp}.wav")
                self._audio_capture = AudioCapture(
                    audio_path,
                    record_mic=self.record_mic,
                    record_system=self.record_system
                )
                if not self._audio_capture.start():
                    self._audio_capture = None

            self.is_recording = True
            self.is_paused = False
            self._start_time = time.time()
            self._paused_duration = 0

            if self.on_status_changed:
                self.on_status_changed("recording")

            print(f"开始录制 {len(self.recorders)} 个视频" +
                  (" + 音频" if self._audio_capture else ""))
            return output_paths

        except Exception as e:
            print(f"启动录制失败: {e}")
            import traceback
            traceback.print_exc()
            return []

    def pause(self):
        """控制器下发暂停指令"""
        if self.is_recording and not self.is_paused:
            self.is_paused = True
            for recorder in self.recorders:
                recorder.pause()
            if self._audio_capture:
                self._audio_capture.pause()

            self._pause_start_time = time.time()
            if self.on_status_changed:
                self.on_status_changed("paused")

    def resume(self):
        """控制器下发恢复指令"""
        if self.is_recording and self.is_paused:
            self.is_paused = False
            for recorder in self.recorders:
                recorder.resume()
            if self._audio_capture:
                self._audio_capture.resume()

            self._paused_duration += time.time() - self._pause_start_time
            if self.on_status_changed:
                self.on_status_changed("recording")

    def stop(self):
        if not self.is_recording:
            return []

        # 1. 停止音频采集
        audio_path = None
        if self._audio_capture:
            audio_path = self._audio_capture.stop()
            self._audio_capture = None

        # 2. 停止视频录制
        for recorder in self.recorders:
            frames = recorder.stop()
            print(f"录制完成: {frames} 帧")

        self.is_recording = False
        self.is_paused = False

        output_paths = [r.output_path for r in self.recorders]

        # 3. 合并音频到视频
        if audio_path and os.path.exists(audio_path):
            from recorder.audio_capture import merge_audio_video
            merged = []
            for vp in output_paths:
                base, ext = os.path.splitext(vp)
                final_path = base + "_merged" + ext
                result = merge_audio_video(vp, audio_path, final_path)
                if result == final_path and os.path.exists(final_path):
                    try:
                        os.remove(vp)
                    except:
                        pass
                    merged.append(final_path)
                else:
                    merged.append(vp)
            output_paths = merged
            try:
                os.remove(audio_path)
            except:
                pass

        if self.on_status_changed:
            self.on_status_changed("stopped")

        for path in output_paths:
            if self.on_recording_complete and os.path.exists(path):
                self.on_recording_complete(path)

        self.recorders = []
        return output_paths

    def get_duration(self):
        """精准计算录制时长（排除暂停时间）"""
        if self.is_recording:
            if self.is_paused:
                # 如果当前正在暂停，时长只算到刚按下暂停的那一刻
                return self._pause_start_time - self._start_time - self._paused_duration
            return time.time() - self._start_time - self._paused_duration
        return 0

    def close(self):
        self.stop()