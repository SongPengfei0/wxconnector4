"""语音条发送的音频底座（可选能力，惰性依赖）。

SendAudio 的原理：微信本身不能"上传音频文件"发语音，只能"按住说话"录麦克风。
本模块把音频文件**播放到虚拟声卡**（VB-CABLE 的 "CABLE Input"），微信麦克风设为
"CABLE Output" 即可把这段音频"听"成你的说话，从而录成语音条发出。

前置条件（缺一不可，均需用户自行配置）：
  1. 安装 VB-CABLE 虚拟声卡（vb-audio.com）；
  2. 微信「设置→音视频→麦克风」选 "CABLE Output"；
  3. pip 安装可选依赖：`pip install sounddevice soundfile numpy`；
  4. 非 wav 音频（mp3/m4a 等）需要 ffmpeg（PATH 或 WxParam.AUDIO_PARAM['ffmpeg_path']）。

本库**不**把上述列为硬依赖，保持轻量；缺失时 SendAudio 给出明确报错。
"""
from __future__ import annotations

import os

from .logger import wxlog


class AudioDepError(RuntimeError):
    """音频可选依赖缺失。"""


def _require(mod_name: str):
    try:
        return __import__(mod_name)
    except Exception as e:
        raise AudioDepError(
            f'SendAudio 需要可选依赖 {mod_name}，请先 `pip install sounddevice soundfile numpy`'
        ) from e


def find_output_device(keyword: str = 'CABLE Input', device_id=None):
    """按名称关键字查找可输出（播放）的声卡设备，返回设备索引。找不到返回 None。"""
    sd = _require('sounddevice')
    if device_id is not None:
        return device_id
    kw = (keyword or '').lower()
    for idx, dev in enumerate(sd.query_devices()):
        try:
            if dev.get('max_output_channels', 0) > 0 and kw in dev['name'].lower():
                return idx
        except Exception:
            continue
    return None


def load_audio(path: str, samplerate=None, ffmpeg_path: str = None):
    """读取音频为 (float32 ndarray[n,ch], samplerate)。

    优先用 soundfile 直接读；读不了（如 mp3/m4a 且 libsndfile 不支持）时用 ffmpeg
    转成临时 wav 再读。samplerate 指定时用 ffmpeg 重采样到该频率。
    """
    np = _require('numpy')
    sf = _require('soundfile')
    if not os.path.exists(path):
        raise FileNotFoundError(path)

    def _read(p):
        data, sr = sf.read(p, dtype='float32', always_2d=True)
        return data, sr

    need_ffmpeg = samplerate is not None
    if not need_ffmpeg:
        try:
            return _read(path)
        except Exception:
            need_ffmpeg = True

    # ffmpeg 兜底/重采样
    import shutil
    import subprocess
    import tempfile
    ff = ffmpeg_path or shutil.which('ffmpeg') or 'ffmpeg'
    tmp = os.path.join(tempfile.gettempdir(), 'wxc4_audio_tmp.wav')
    cmd = [ff, '-y', '-i', path]
    if samplerate:
        cmd += ['-ar', str(int(samplerate))]
    cmd += [tmp]
    try:
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    except Exception as e:
        raise AudioDepError(f'ffmpeg 转码失败（确认已安装 ffmpeg 或音频可读）: {e}') from e
    data, sr = _read(tmp)
    try:
        os.remove(tmp)
    except Exception:
        pass
    return data, sr


def slice_audio(data, samplerate, start: float = 0, duration: float = None):
    """按 start/duration（秒）裁剪音频。"""
    s = max(0, int(start * samplerate))
    if duration:
        e = min(len(data), s + int(duration * samplerate))
    else:
        e = len(data)
    return data[s:e]


def play_to_device(data, samplerate, device, channels=None, blocking: bool = True):
    """把音频数据播放到指定设备（虚拟声卡）。blocking=True 时阻塞到放完。

    channels 仅作占位（声道由 data 形状推断；mono/stereo 由 sounddevice 自适应）。
    """
    sd = _require('sounddevice')
    sd.play(data, samplerate=samplerate, device=device)
    if blocking:
        sd.wait()


def audio_seconds(data, samplerate) -> float:
    try:
        return round(len(data) / float(samplerate), 2)
    except Exception:
        return 0.0
