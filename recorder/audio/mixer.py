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

    cmd = ['ffmpeg', '-y', '-i', video_path]

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
