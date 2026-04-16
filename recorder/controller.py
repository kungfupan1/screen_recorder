# -*- coding: utf-8 -*-
"""
录制控制器 - 包含完整的控制、暂停/恢复、多屏幕及区域录制支持
"""
import threading
import time
import mss
import subprocess
import os
import json
from datetime import datetime
import numpy as np
from queue import Queue, Empty


class ScreenRecorder:
    """单个屏幕录制器"""

    _cached_encoder = None  # 内存缓存（会话内复用）

    @classmethod
    def _encoder_cache_path(cls):
        return os.path.join(os.environ.get('LOCALAPPDATA', ''), '录屏王', 'encoder_cache.json')

    @classmethod
    def _load_encoder_cache(cls):
        """从磁盘读取缓存的编码器名称"""
        try:
            with open(cls._encoder_cache_path(), 'r') as f:
                data = json.load(f)
                return data.get('encoder')
        except:
            return None

    @classmethod
    def _save_encoder_cache(cls, encoder):
        """将编码器名称写入磁盘缓存"""
        try:
            path = cls._encoder_cache_path()
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'w') as f:
                json.dump({'encoder': encoder}, f)
        except:
            pass

    @classmethod
    def _detect_encoder(cls, ffmpeg_path):
        """探测可用的 H.264 编码器（内存→磁盘→实时探测）"""
        # 1. 内存缓存
        if cls._cached_encoder is not None:
            return cls._cached_encoder

        # 2. 磁盘缓存
        cached = cls._load_encoder_cache()
        if cached:
            cls._cached_encoder = cached
            return cached

        # 3. 实时探测
        for encoder in ['h264_nvenc', 'h264_amf', 'h264_qsv', 'libopenh264']:
            try:
                startupinfo = None
                if os.name == 'nt':
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                result = subprocess.run(
                    [ffmpeg_path, '-hide_banner', '-loglevel', 'error',
                     '-f', 'lavfi', '-i', 'nullsrc=s=64x64:d=0.1',
                     '-c:v', encoder, '-f', 'null', '-'],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    startupinfo=startupinfo, timeout=3
                )
                if result.returncode == 0:
                    cls._cached_encoder = encoder
                    cls._save_encoder_cache(encoder)
                    return encoder
            except:
                pass

        cls._cached_encoder = 'mpeg4'
        cls._save_encoder_cache('mpeg4')
        return 'mpeg4'

    def __init__(self, bounds, output_path, fps=30, watermark=False):
        x, y, w, h = [int(v) for v in bounds]
        self.width = w if w % 2 == 0 else w - 1
        self.height = h if h % 2 == 0 else h - 1
        self.bounds = (x, y, self.width, self.height)

        self.output_path = output_path
        self.fps = fps
        self._watermark = watermark

        self._ffmpeg_proc = None
        self.frame_count = 0
        self.queue = Queue(maxsize=120)
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._capture_thread = None
        self._write_thread = None
        self._wm_overlay = None  # 预渲染的水印 RGBA 图层

    def pause(self):
        """暂停录制"""
        self._pause_event.set()

    def resume(self):
        """恢复录制"""
        self._pause_event.clear()

    def start(self):
        """初始化并开始录制 (FFmpeg pipe, 自动探测编码器)"""
        from utils.config import get_resource_path

        encoder = self._detect_encoder(get_resource_path('ffmpeg'))

        ffmpeg_cmd = [
            get_resource_path('ffmpeg'),
            '-y',
            '-f', 'rawvideo',
            '-vcodec', 'rawvideo',
            '-pix_fmt', 'bgr24',
            '-s', f'{self.width}x{self.height}',
            '-r', str(self.fps),
            '-i', '-',
        ]

        if encoder == 'h264_nvenc':
            ffmpeg_cmd += ['-c:v', 'h264_nvenc', '-preset', 'p1', '-tune', 'ull', '-cq', '20', '-pix_fmt', 'yuv420p']
        elif encoder == 'h264_amf':
            ffmpeg_cmd += ['-c:v', 'h264_amf', '-quality', 'speed', '-rc', 'cqp', '-qp_i', '20', '-qp_p', '20', '-pix_fmt', 'yuv420p']
        elif encoder == 'h264_qsv':
            ffmpeg_cmd += ['-c:v', 'h264_qsv', '-preset', 'veryfast', '-global_quality', '20', '-look_ahead', '0']
        elif encoder == 'libopenh264':
            ffmpeg_cmd += ['-c:v', 'libopenh264', '-pix_fmt', 'yuv420p']
        else:
            # fallback: mpeg4 (跟原 mp4v 相同质量)
            ffmpeg_cmd += ['-c:v', 'mpeg4', '-q:v', '3']

        ffmpeg_cmd += ['-movflags', '+faststart', self.output_path]

        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        self._ffmpeg_proc = subprocess.Popen(
            ffmpeg_cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            startupinfo=startupinfo
        )

        # 容错：如果缓存的编码器不可用（如换了显卡），FFmpeg 会立即退出
        if self._ffmpeg_proc.poll() is not None and self._ffmpeg_proc.returncode != 0:
            # 清除缓存，重新探测
            ScreenRecorder._cached_encoder = None
            try:
                os.remove(ScreenRecorder._encoder_cache_path())
            except:
                pass
            encoder = ScreenRecorder._detect_encoder(get_resource_path('ffmpeg'))
            # 重建 FFmpeg 命令并重试
            ffmpeg_cmd = [
                get_resource_path('ffmpeg'), '-y',
                '-f', 'rawvideo', '-vcodec', 'rawvideo',
                '-pix_fmt', 'bgr24',
                '-s', f'{self.width}x{self.height}',
                '-r', str(self.fps), '-i', '-',
            ]
            if encoder == 'h264_nvenc':
                ffmpeg_cmd += ['-c:v', 'h264_nvenc', '-preset', 'p1', '-tune', 'ull', '-cq', '20', '-pix_fmt', 'yuv420p']
            elif encoder == 'h264_amf':
                ffmpeg_cmd += ['-c:v', 'h264_amf', '-quality', 'speed', '-rc', 'cqp', '-qp_i', '20', '-qp_p', '20', '-pix_fmt', 'yuv420p']
            elif encoder == 'h264_qsv':
                ffmpeg_cmd += ['-c:v', 'h264_qsv', '-preset', 'veryfast', '-global_quality', '20', '-look_ahead', '0']
            elif encoder == 'libopenh264':
                ffmpeg_cmd += ['-c:v', 'libopenh264', '-pix_fmt', 'yuv420p']
            else:
                ffmpeg_cmd += ['-c:v', 'mpeg4', '-q:v', '3']
            ffmpeg_cmd += ['-movflags', '+faststart', self.output_path]
            self._ffmpeg_proc = subprocess.Popen(
                ffmpeg_cmd, stdin=subprocess.PIPE,
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                startupinfo=startupinfo
            )

        self._capture_thread = threading.Thread(target=self._capture_worker, daemon=True)
        self._capture_thread.start()

        self._write_thread = threading.Thread(target=self._write_worker, daemon=True)
        self._write_thread.start()

        return True

    def _build_watermark(self):
        """预渲染水印图层（只调用一次，后续逐帧叠加零开销）"""
        try:
            from PIL import Image, ImageDraw, ImageFont
        except ImportError:
            print("[Watermark] Pillow 未安装，跳过水印")
            return

        w, h = self.width, self.height
        # 水印尺寸约为视频的 1/15 高度
        font_size = max(12, h // 15)
        margin = max(20, h // 25)

        # 加载幼圆字体
        font_paths = [
            os.path.join(os.environ.get('SystemRoot', r'C:\Windows'), 'Fonts', 'SIMYOU.TTF'),
            os.path.join(os.environ.get('SystemRoot', r'C:\Windows'), 'Fonts', 'simyou.ttf'),
        ]
        font = None
        for fp in font_paths:
            if os.path.exists(fp):
                try:
                    font = ImageFont.truetype(fp, font_size)
                    break
                except:
                    pass
        if font is None:
            font = ImageFont.load_default()

        # 计算文字尺寸
        tmp = Image.new('RGBA', (1, 1))
        draw = ImageDraw.Draw(tmp)
        text = "录屏王"
        bbox = draw.textbbox((0, 0), text, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]

        # 创建水印图层
        layer = Image.new('RGBA', (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(layer)
        # 水印位置：右下角，留边距
        x = w - tw - margin
        y = h - th - margin
        # 描边（深灰色描边增加对比度）
        stroke_w = max(2, font_size // 15)
        for dx in range(-stroke_w, stroke_w + 1):
            for dy in range(-stroke_w, stroke_w + 1):
                if dx * dx + dy * dy <= stroke_w * stroke_w:
                    draw.text((x + dx, y + dy), text, font=font, fill=(0, 0, 0, 160))
        # 主文字（半透明白色）
        draw.text((x, y), text, font=font, fill=(255, 255, 255, 140))

        self._wm_overlay = np.array(layer)  # RGBA numpy array

    def _apply_watermark(self, frame):
        """将预渲染水印叠加到 BGR 帧上"""
        overlay = self._wm_overlay
        if overlay is None:
            return frame
        # overlay 是 RGBA，frame 是 BGR
        alpha = overlay[:, :, 3:4].astype(np.float32) / 255.0
        rgb = overlay[:, :, :3][:, :, ::-1]  # RGBA → BGR
        blended = (frame.astype(np.float32) * (1.0 - alpha) + rgb.astype(np.float32) * alpha)
        return blended.astype(np.uint8)

    def _capture_worker(self):
        """捕获线程 - 增加帧率同步与补帧逻辑"""
        # 免费版水印：预渲染一次（失败不影响录制）
        if self._watermark:
            try:
                self._build_watermark()
            except Exception as e:
                print(f"[Watermark] 预渲染失败: {e}，跳过水印")
                self._wm_overlay = None

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

                    # 免费版水印叠加
                    if self._wm_overlay is not None:
                        frame = self._apply_watermark(frame)

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
        """写入线程 - 将帧写入 FFmpeg stdin"""
        while not self._stop_event.is_set() or not self.queue.empty():
            try:
                frame = self.queue.get(timeout=0.5)
                if self._ffmpeg_proc and self._ffmpeg_proc.poll() is None:
                    try:
                        self._ffmpeg_proc.stdin.write(frame.tobytes())
                        self.frame_count += 1
                    except (BrokenPipeError, OSError):
                        break
            except Empty:
                continue

        # 关闭 FFmpeg stdin，让 FFmpeg 正常 flush 输出
        if self._ffmpeg_proc:
            try:
                self._ffmpeg_proc.stdin.close()
            except:
                pass

    def stop(self):
        """停止录制"""
        self._stop_event.set()
        self._pause_event.clear()  # 防死锁

        if self._capture_thread and self._capture_thread.is_alive():
            self._capture_thread.join(timeout=2.0)
        if self._write_thread and self._write_thread.is_alive():
            self._write_thread.join(timeout=10.0)

        if self._ffmpeg_proc:
            try:
                self._ffmpeg_proc.wait(timeout=5.0)
            except subprocess.TimeoutExpired:
                self._ffmpeg_proc.kill()
            self._ffmpeg_proc = None

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

        # 免费版水印
        self.free_mode = False

        # 保存中标志（防止保存未完成时开始新录制）
        self._saving = False

        self.on_status_changed = None
        self.on_recording_complete = None

        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # 后台预初始化音频子系统（PyAudio + WASAPI 设备探测）
        # 首次约 300-500ms，后续录制直接复用缓存，点击录制几乎无延迟
        threading.Thread(target=self._preinit_audio, daemon=True).start()

    def _preinit_audio(self):
        try:
            from recorder.audio import preinit_audio
            preinit_audio()
        except:
            pass
        # 同时预探测 FFmpeg 编码器（首次约 1-2s，结果写入磁盘缓存）
        try:
            from utils.config import get_resource_path
            ScreenRecorder._detect_encoder(get_resource_path('ffmpeg'))
        except:
            pass

    @staticmethod
    def get_monitors():
        with mss.mss() as sct:
            return sct.monitors[1:]

    def set_monitors(self, indices):
        self.selected_monitors = indices  # 允许 [] 表示纯录音模式
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
                    recorder = ScreenRecorder(self.region, output, self.fps, watermark=self.free_mode)
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

                        recorder = ScreenRecorder(bounds, output, self.fps, watermark=self.free_mode)
                        recorder.start()
                        self.recorders.append(recorder)
                        output_paths.append(output)

            if not self.recorders:
                # 纯音频模式：无视频录制，必须有音频
                if not (self.record_mic or self.record_system):
                    raise RuntimeError("没有有效的录制目标")

            # 启动音频采集 (多轨独立录制)
            self._audio_capture = None
            if self.record_mic or self.record_system:
                from recorder.audio import AudioCapture
                self._audio_capture = AudioCapture(
                    self.output_dir,
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

            if self.recorders:
                print(f"开始录制 {len(self.recorders)} 个视频" +
                      (" + 音频" if self._audio_capture else ""))
            else:
                print("开始纯音频录制" +
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
        audio_paths = {}
        if self._audio_capture:
            audio_paths = self._audio_capture.stop()
            self._audio_capture = None

        # 2. 信号通知所有录制器停止（瞬间完成，不阻塞）
        for recorder in self.recorders:
            recorder._stop_event.set()
            recorder._pause_event.clear()

        self.is_recording = False
        self.is_paused = False
        self._saving = True

        output_paths = [r.output_path for r in self.recorders]
        recorders_snapshot = list(self.recorders)
        self.recorders = []

        if self.on_status_changed:
            self.on_status_changed("stopped")

        # 3. 后台清理：并行等待线程结束 + FFmpeg flush + 音频合并
        def _background_cleanup():
            # 并行清理所有 recorder
            def _cleanup_one(rec):
                if rec._capture_thread and rec._capture_thread.is_alive():
                    rec._capture_thread.join(timeout=2.0)
                if rec._write_thread and rec._write_thread.is_alive():
                    rec._write_thread.join(timeout=10.0)
                if rec._ffmpeg_proc:
                    try:
                        rec._ffmpeg_proc.wait(timeout=5.0)
                    except subprocess.TimeoutExpired:
                        rec._ffmpeg_proc.kill()
                    rec._ffmpeg_proc = None
                print(f"录制完成: {rec.frame_count} 帧")

            cleanup_threads = []
            for rec in recorders_snapshot:
                t = threading.Thread(target=_cleanup_one, args=(rec,))
                t.start()
                cleanup_threads.append(t)
            for t in cleanup_threads:
                t.join()

            # 音频合并
            if audio_paths:
                if output_paths:
                    from recorder.audio import merge_tracks
                    merged = []
                    for vp in output_paths:
                        base, ext = os.path.splitext(vp)
                        final_path = base + "_merged" + ext
                        result = merge_tracks(vp, audio_paths, final_path)
                        if result == final_path and os.path.exists(final_path):
                            try:
                                os.remove(vp)
                            except:
                                pass
                            merged.append(final_path)
                        else:
                            merged.append(vp)
                    for name, ap in audio_paths.items():
                        try:
                            os.remove(ap)
                        except:
                            pass
                    for path in merged:
                        if self.on_recording_complete and os.path.exists(path):
                            self.on_recording_complete(path)
                    print(f"[合并完成] {len(merged)} 个视频已合并 {len(audio_paths)} 条音轨")
                else:
                    from recorder.audio.mixer import merge_audio_only
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    mp3_path = os.path.join(self.output_dir, f"recording_{timestamp}.mp3")
                    result = merge_audio_only(audio_paths, mp3_path)
                    if result and self.on_recording_complete and os.path.exists(result):
                        self.on_recording_complete(result)
                    print(f"[纯录音完成] 输出: {result}")
            else:
                for path in output_paths:
                    if self.on_recording_complete and os.path.exists(path):
                        self.on_recording_complete(path)

            self._saving = False

        threading.Thread(target=_background_cleanup, daemon=True).start()

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