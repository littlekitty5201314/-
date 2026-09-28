# -*- coding: utf-8 -*-
"""
视频溯源智能体 —— ASR 模块（本地语音转写）

基于 faster-whisper，将视频音频转为文字，全程本地运行。
"""
import os
import subprocess
from pathlib import Path

import config

# 固化 whisper 模型下载/加载的网络环境（国内镜像），
# 避免因默认 HuggingFace 源被墙导致模型加载失败。
# 注意：不设置 HF_HUB_OFFLINE，这样新电脑首次运行能自动从镜像下载模型，
# 本机已有缓存时会直接复用缓存、不联网。
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

_ASR_MODEL = None


def extract_audio(video_path: Path) -> Path:
    """用 ffmpeg 从视频中抽取音频。"""
    config.AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    audio_path = config.AUDIO_DIR / (video_path.stem + ".wav")
    cmd = [
        "ffmpeg", "-i", str(video_path),
        "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
        "-y", str(audio_path),
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    except FileNotFoundError:
        raise RuntimeError("未找到 ffmpeg，请先安装 ffmpeg 并加入 PATH")
    if not audio_path.exists():
        raise RuntimeError(f"音频抽取失败：{proc.stderr.strip()[:200]}")
    return audio_path


def _load_model():
    """懒加载 ASR 模型。"""
    global _ASR_MODEL
    if _ASR_MODEL is not None:
        return _ASR_MODEL
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        raise RuntimeError("未安装 faster-whisper，请运行：pip install faster-whisper")
    _ASR_MODEL = WhisperModel(
        config.ASR_MODEL_SIZE,
        device="cpu",
        compute_type="int8",
    )
    return _ASR_MODEL


def transcribe(video_path: Path) -> str:
    """抽取音频并转写为文字。"""
    audio_path = extract_audio(video_path)
    model = _load_model()
    language = None if config.ASR_LANGUAGE == "auto" else config.ASR_LANGUAGE
    segments, info = model.transcribe(
        str(audio_path),
        language=language,
        vad_filter=True,
        beam_size=5,
    )
    parts = [seg.text.strip() for seg in segments]
    return "".join(parts)
