"""
音频落盘公共工具

统一 numpy 音频 → WAV 文件的写盘逻辑（soundfile 优先，标准库 wave 回退），
供 adapter（LocalVoiceAdapter）与 workers（TTSEngine 等）复用，避免重复实现。
"""
from __future__ import annotations

from pathlib import Path
from typing import Union

import numpy as np

# 16-bit 有符号整数归一化除数（2^15，用于 int16 → float [-1, 1)）
_INT16_SCALE = 32768.0


def _to_float_mono(audio: np.ndarray) -> np.ndarray:
    """
    将任意 numpy 音频转换为单声道 float32 [-1, 1]

    Args:
        audio: int16/uint8/int/float 数组

    Returns:
        单声道 float32 数组，范围 [-1, 1]
    """
    audio = np.asarray(audio).squeeze()
    if audio.ndim > 1:
        # 多声道 → 取均值转单声道
        audio = audio.mean(axis=-1)

    if audio.dtype == np.int16:
        audio = audio.astype(np.float32) / _INT16_SCALE
    elif np.issubdtype(audio.dtype, np.integer):
        audio = audio.astype(np.float32) / (np.iinfo(audio.dtype).max + 1.0)
    else:
        audio = audio.astype(np.float32)

    return np.clip(audio, -1.0, 1.0)


def save_audio_to_wav(
    audio: np.ndarray,
    sample_rate: int,
    output_path: Union[str, Path],
) -> Path:
    """
    将 numpy 音频落盘为 WAV 文件

    优先使用 soundfile；不可用时回退到标准库 wave 写入 16-bit PCM WAV。
    自动补齐 `.wav` 后缀，并确保父目录存在。

    Args:
        audio: 音频数据（int16/int/float 均可，自动转为单声道 float32 [-1,1]）
        sample_rate: 采样率（Hz）
        output_path: 输出路径（无 .wav 后缀会自动补齐）

    Returns:
        实际写入的 WAV 文件路径
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    audio = _to_float_mono(audio)
    if output_path.suffix.lower() != ".wav":
        output_path = output_path.with_suffix(".wav")

    try:
        import soundfile as sf
        sf.write(str(output_path), audio, sample_rate)
    except ImportError:
        pcm = (audio * 32767.0).astype(np.int16)
        import wave
        with wave.open(str(output_path), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(pcm.tobytes())

    return output_path
