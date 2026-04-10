# -*- coding: utf-8 -*-
"""
音频设备发现 - 麦克风与 WASAPI Loopback
"""

try:
    import pyaudiowpatch as pyaudio
    HAS_AUDIO = True
except ImportError:
    HAS_AUDIO = False

# 模块级设备信息缓存（首次探测后复用，避免每次录制重新枚举 WASAPI 设备）
_device_cache = None


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


def get_cached_devices(pa):
    """获取设备信息（首次调用时探测并缓存，后续直接复用）"""
    global _device_cache
    if _device_cache is None:
        _device_cache = {
            'mic': find_mic_device(pa),
            'sys': find_loopback_device(pa),
        }
    return _device_cache


def refresh_device_cache(pa):
    """强制刷新设备缓存（设备热插拔后调用）"""
    global _device_cache
    _device_cache = {
        'mic': find_mic_device(pa),
        'sys': find_loopback_device(pa),
    }
