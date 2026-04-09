# -*- coding: utf-8 -*-
"""
音频设备发现 - 麦克风与 WASAPI Loopback
"""

try:
    import pyaudiowpatch as pyaudio
    HAS_AUDIO = True
except ImportError:
    HAS_AUDIO = False


def find_mic_device(pa):
    """查找默认麦克风设备

    Returns:
        dict: {'index', 'name', 'sample_rate', 'channels'} 或 None
    """
    try:
        info = pa.get_default_input_device_info()
        return {
            'index': info['index'],
            'name': info['name'],
            'sample_rate': int(info['defaultSampleRate']),
            'channels': min(info['maxInputChannels'], 2),
        }
    except Exception as e:
        print(f"[AudioSource] 麦克风设备查找失败: {e}")
        return None


def find_loopback_device(pa):
    """查找 WASAPI Loopback 设备 (系统声音)

    Returns:
        dict: {'index', 'name', 'sample_rate', 'channels'} 或 None
    """
    try:
        wasapi_info = pa.get_host_api_info_by_type(pyaudio.paWASAPI)
        speakers = pa.get_device_info_by_index(wasapi_info["defaultOutputDevice"])

        loopback = None
        if speakers.get("isLoopbackDevice"):
            loopback = speakers
        else:
            for dev in pa.get_loopback_device_info_generator():
                if speakers["name"] in dev["name"]:
                    loopback = dev
                    break

        if not loopback:
            print("[AudioSource] 未找到 WASAPI Loopback 设备")
            return None

        return {
            'index': loopback['index'],
            'name': loopback['name'],
            'sample_rate': int(loopback['defaultSampleRate']),
            'channels': min(loopback['maxInputChannels'], 2),
        }
    except Exception as e:
        print(f"[AudioSource] 系统音频设备查找失败: {e}")
        return None
