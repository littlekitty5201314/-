# -*- coding: utf-8 -*-
"""
视频溯源智能体 —— 视频分析模块（ffmpeg）

功能：
1. 判断视频是否存在剪辑（基于场景切换检测）
2. 提取关键帧
"""
import json
import subprocess
from pathlib import Path

import config


def _run_ffprobe(video_path: Path) -> dict:
    """调用 ffprobe 获取视频元信息。"""
    cmd = [
        "ffprobe", "-v", "error",
        "-print_format", "json",
        "-show_format", "-show_streams",
        str(video_path),
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr.strip())
        return json.loads(proc.stdout)
    except FileNotFoundError:
        raise RuntimeError("未找到 ffprobe，请先安装 ffmpeg 并加入 PATH")


def get_video_info(video_path: Path) -> dict:
    """获取视频基本信息：时长、分辨率、编码、帧率等。"""
    data = _run_ffprobe(video_path)
    video_stream = next(
        (s for s in data.get("streams", []) if s.get("codec_type") == "video"),
        None,
    )
    fmt = data.get("format", {})
    duration = float(fmt.get("duration", 0) or 0)
    return {
        "path": str(video_path),
        "name": video_path.name,
        "duration": duration,
        "width": video_stream.get("width") if video_stream else None,
        "height": video_stream.get("height") if video_stream else None,
        "fps": video_stream.get("r_frame_rate") if video_stream else None,
        "codec": video_stream.get("codec_name") if video_stream else None,
    }


def detect_scene_changes(video_path: Path, threshold: float = None) -> list:
    """
    检测场景切换，返回每个切换点的时间（秒）。

    原理：使用 ffmpeg 的 scene 滤镜，当相邻两帧差异超过阈值时
    认为发生了一次镜头切换（剪辑点）。
    """
    threshold = threshold if threshold is not None else config.SCENE_THRESHOLD
    cmd = [
        "ffmpeg", "-nostdin",
        "-i", str(video_path),
        "-filter:v", f"select='gt(scene,{threshold})',showinfo",
        "-f", "null", "-",
    ]
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=300,
        )
    except FileNotFoundError:
        raise RuntimeError("未找到 ffmpeg，请先安装 ffmpeg 并加入 PATH")

    # showinfo 输出形如：pts_time:12.345
    times = []
    for line in (proc.stderr or "").splitlines():
        if "pts_time:" in line:
            try:
                t = line.split("pts_time:")[1].strip().split()[0]
                times.append(round(float(t), 2))
            except (ValueError, IndexError):
                continue
    return times


def judge_edited(scene_times: list, duration: float) -> dict:
    """
    判断视频是否经过剪辑。

    启发式规则：
    - 场景切换次数 >= 阈值 则认为可能被剪辑
    - 剪辑密集度（切换次数 / 每分钟）越高，剪辑可能性越大
    """
    cut_count = len(scene_times)
    edited = cut_count >= config.MIN_SCENE_CUTS
    # 每分钟剪辑点数
    density = (cut_count / (duration / 60)) if duration > 0 else 0
    confidence = min(0.99, 0.3 + density * 0.1) if edited else max(0.05, 1 - density * 0.1)
    confidence = round(confidence, 2)
    return {
        "edited": edited,
        "cut_count": cut_count,
        "scene_times": scene_times,
        "confidence": confidence,
        "density_per_min": round(density, 2),
    }


def _clean_keyframe_dir():
    """清空关键帧目录，避免上一个视频的旧帧混入本次 OCR 结果。"""
    config.KEYFRAME_DIR.mkdir(parents=True, exist_ok=True)
    for old in config.KEYFRAME_DIR.glob("*.jpg"):
        try:
            old.unlink()
        except OSError:
            pass


def extract_keyframes(
    video_path: Path,
    interval: int = None,
    scene_times: list = None,
) -> list:
    """
    提取关键帧：
    1. 按固定间隔抽帧
    2. 在场景切换点精确抽帧

    返回关键帧文件路径列表。
    """
    interval = interval if interval is not None else config.KEYFRAME_INTERVAL
    scene_times = scene_times or []
    _clean_keyframe_dir()

    frames = []

    # 1) 按间隔抽帧（-y 覆盖输出、-nostdin 禁用交互，防止卡死）
    interval_pattern = str(config.KEYFRAME_DIR / "frame_%04d.jpg")
    cmd_interval = [
        "ffmpeg", "-nostdin", "-y",
        "-i", str(video_path),
        "-vf", f"fps=1/{interval}",
        "-q:v", "2",
        interval_pattern,
    ]
    try:
        proc = subprocess.run(cmd_interval, capture_output=True, text=True, timeout=300)
        if not config.KEYFRAME_DIR.glob("frame_*.jpg"):
            err = (proc.stderr or "").strip().splitlines()
            raise RuntimeError("间隔抽帧失败：" + (err[-1] if err else "未知错误"))
    except FileNotFoundError:
        raise RuntimeError("未找到 ffmpeg，请先安装 ffmpeg 并加入 PATH")

    frames.extend(sorted(config.KEYFRAME_DIR.glob("frame_*.jpg")))

    # 2) 场景切换点抽帧（-nostdin 禁用交互）
    for i, t in enumerate(scene_times):
        scene_path = config.KEYFRAME_DIR / f"scene_{i:03d}_{t}.jpg"
        cmd_scene = [
            "ffmpeg", "-nostdin", "-y",
            "-ss", str(t), "-i", str(video_path),
            "-frames:v", "1", "-q:v", "2", str(scene_path),
        ]
        subprocess.run(cmd_scene, capture_output=True, text=True, timeout=120)
        if scene_path.exists():
            frames.append(scene_path)

    return frames


def analyze(video_path: Path) -> dict:
    """完整视频分析：信息 + 剪辑判断 + 关键帧提取。"""
    print("  1a. 读取视频信息（ffprobe）...")
    info = get_video_info(video_path)
    print(f"  1b. 场景切换检测中（需完整解码视频，长视频约需 1-2 分钟）...")
    scene_times = detect_scene_changes(video_path)
    print(f"  1b. 完成，检测到 {len(scene_times)} 个场景切换点")
    edit_result = judge_edited(scene_times, info["duration"])
    print("  1c. 提取关键帧...")
    keyframes = extract_keyframes(video_path, scene_times=scene_times)
    print(f"  1c. 完成，共 {len(keyframes)} 帧")
    return {
        **info,
        **edit_result,
        "keyframes": [str(p) for p in keyframes],
        "keyframe_count": len(keyframes),
    }
