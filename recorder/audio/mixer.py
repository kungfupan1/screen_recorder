# -*- coding: utf-8 -*-
"""
音视频合并 - 动态 FFmpeg 多轨合并

根据音轨数量自动选择策略:
  0 条音轨 → 直接拷贝视频
  1 条音轨 → 直接嵌入 (不用 amix)
  2+ 条音轨 → amix 混音
所有场景加 aresample=async=1 防时钟漂移
"""

import os
import subprocess

from utils.config import get_resource_path


def merge_tracks(video_path, audio_paths, output_path):
    """将视频与多条音轨合并

    Args:
        video_path: 视频文件路径
        audio_paths: 音频文件字典 {"mic": "path/to/mic.wav", "sys": "path/to/sys.wav"}
                     值为 None 的条目会被跳过
        output_path: 输出文件路径
    Returns:
        最终输出文件路径 (失败时返回原视频路径)
    """
    if not os.path.exists(video_path):
        return video_path

    # 过滤掉 None 和不存在的文件
    valid_audio = {}
    for name, path in audio_paths.items():
        if path and os.path.exists(path):
            valid_audio[name] = path

    if not valid_audio:
        return video_path

    try:
        cmd = _build_ffmpeg_cmd(video_path, valid_audio, output_path)

        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        print(f"[合并中] 正在合并 {len(valid_audio)} 条音轨到视频...")

        result = subprocess.run(
            cmd,
            startupinfo=startupinfo,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30
        )

        if result.returncode == 0 and os.path.exists(output_path):
            print("[合并成功] 音视频已完美融合！")
            return output_path
        else:
            print(f"[合并失败] FFmpeg 返回码: {result.returncode}")
            print(result.stderr.decode('utf-8', errors='ignore'))
            return video_path

    except FileNotFoundError:
        print("[致命错误] 系统未安装 FFmpeg！")
        return video_path
    except Exception as e:
        print(f"[合并异常] {e}")
        return video_path


def _build_ffmpeg_cmd(video_path, audio_paths, output_path):
    """动态构建 FFmpeg 命令"""
    audio_list = list(audio_paths.values())
    num_tracks = len(audio_list)

    cmd = [get_resource_path('ffmpeg'), '-y', '-i', video_path]

    for path in audio_list:
        cmd.extend(['-i', path])

    if num_tracks == 1:
        # 单轨: 直接嵌入 + 抗漂移
        cmd.extend([
            '-filter_complex', '[1:a]aresample=async=1:first_pts=0[a]',
            '-map', '0:v', '-map', '[a]',
            '-c:v', 'copy', '-c:a', 'aac',
            output_path
        ])
    else:
        # 多轨: 逐条抗漂移 + amix 混音
        filter_parts = []
        mix_inputs = []
        for i in range(num_tracks):
            label = f'a{i}'
            filter_parts.append(f'[{i + 1}:a]aresample=async=1:first_pts=0[{label}]')
            mix_inputs.append(f'[{label}]')

        mix_str = ''.join(mix_inputs)
        filter_parts.append(
            f'{mix_str}amix=inputs={num_tracks}:duration=longest[a]'
        )
        filter_complex = '; '.join(filter_parts)

        cmd.extend([
            '-filter_complex', filter_complex,
            '-map', '0:v', '-map', '[a]',
            '-c:v', 'copy', '-c:a', 'aac',
            '-shortest',
            output_path
        ])

    return cmd


def merge_audio_only(audio_paths, output_path):
    """将多条 WAV 音轨合并转换为 MP3 (纯录音模式)

    Args:
        audio_paths: 音频文件字典 {"mic": "path/to/mic.wav", "sys": "path/to/sys.wav"}
                     值为 None 的条目会被跳过
        output_path: 输出文件路径 (.mp3)
    Returns:
        最终输出文件路径 (失败时返回第一条有效音频路径)
    """
    valid_audio = {}
    for name, path in audio_paths.items():
        if path and os.path.exists(path):
            valid_audio[name] = path

    if not valid_audio:
        return None

    audio_list = list(valid_audio.values())

    # 尝试 libmp3lame → 失败则降级 aac
    for codec, ext in [("libmp3lame", ".mp3"), ("aac", ".m4a")]:
        if ext != os.path.splitext(output_path)[1].lower():
            output_path = os.path.splitext(output_path)[0] + ext

        try:
            cmd = _build_audio_only_cmd(audio_list, output_path, codec)

            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            print(f"[纯录音] 正在转换 {len(audio_list)} 条音轨为 {ext}...")

            result = subprocess.run(
                cmd,
                startupinfo=startupinfo,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=60
            )

            if result.returncode == 0 and os.path.exists(output_path):
                print(f"[纯录音成功] 已输出: {output_path}")
                # 清理临时 WAV
                for ap in audio_list:
                    try:
                        os.remove(ap)
                    except:
                        pass
                return output_path
            else:
                err = result.stderr.decode('utf-8', errors='ignore')
                # 如果是编码器不支持，尝试下一个
                if 'Unknown encoder' in err or 'not found' in err:
                    print(f"[纯录音] {codec} 不支持，尝试降级编码器...")
                    continue
                print(f"[纯录音失败] FFmpeg 返回码: {result.returncode}")
                print(err)

        except FileNotFoundError:
            print("[致命错误] 系统未安装 FFmpeg！")
            return audio_list[0]
        except subprocess.TimeoutExpired:
            print("[纯录音超时] WAV→MP3 编码超时")
            return audio_list[0]
        except Exception as e:
            print(f"[纯录音异常] {e}")
            return audio_list[0]

    # 所有编码器都失败，返回原始 WAV
    return audio_list[0]


def _build_audio_only_cmd(audio_list, output_path, codec):
    """构建纯音频 FFmpeg 命令"""
    cmd = [get_resource_path('ffmpeg'), '-y']

    for path in audio_list:
        cmd.extend(['-i', path])

    if len(audio_list) == 1:
        # 单轨: 直接转码
        cmd.extend(['-c:a', codec])
        if codec == 'libmp3lame':
            cmd.extend(['-q:a', '2'])
    else:
        # 多轨: aresample + amix → 编码输出
        filter_parts = []
        mix_inputs = []
        for i in range(len(audio_list)):
            label = f'a{i}'
            filter_parts.append(f'[{i}:a]aresample=async=1:first_pts=0[{label}]')
            mix_inputs.append(f'[{label}]')
        mix_str = ''.join(mix_inputs)
        filter_parts.append(
            f'{mix_str}amix=inputs={len(audio_list)}:duration=longest[a]'
        )
        filter_complex = '; '.join(filter_parts)
        cmd.extend(['-filter_complex', filter_complex, '-map', '[a]'])
        cmd.extend(['-c:a', codec])
        if codec == 'libmp3lame':
            cmd.extend(['-q:a', '2'])

    cmd.append(output_path)
    return cmd
