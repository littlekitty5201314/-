# -*- coding: utf-8 -*-
"""
视频溯源智能体 —— 全局配置

所有可调参数集中在这里。
"""
import os
from pathlib import Path

# 项目根目录（本文件所在目录）
BASE_DIR = Path(__file__).resolve().parent

# 工作目录
DATA_DIR = BASE_DIR / "data"
KEYFRAME_DIR = DATA_DIR / "keyframes"          # 关键帧输出目录
AUDIO_DIR = DATA_DIR / "audio"                  # 抽取音频输出目录
OUTPUT_DIR = BASE_DIR / "output"                # 最终报告输出目录
RESULTS_DIR = BASE_DIR / "results"              # 三个网站抓取结果目录

# 关键文件
KEYWORDS_FILE = BASE_DIR / "keywords.json"      # 关键词（置信度排序）
REPORT_FILE = OUTPUT_DIR / "溯源报告.md"        # 最终报告

# ============ 视频分析（ffmpeg） ============
# 关键帧抽取间隔（秒）
KEYFRAME_INTERVAL = 2
# 场景切换判定阈值（ffmpeg scene 分数，越低越敏感）
SCENE_THRESHOLD = 0.35
# 判定"有剪辑"的最少场景切换次数
MIN_SCENE_CUTS = 2

# ============ OCR / ASR ============
# OCR 引擎：rapidocr / easyocr / tesseract
OCR_ENGINE = "rapidocr"
# ASR 模型大小：tiny / base / small / medium / large
ASR_MODEL_SIZE = "small"
# ASR 语言：zh / en / 自动
ASR_LANGUAGE = "zh"

# ============ 千问大模型 ============
# 通义千问 API Key（也可通过环境变量 DASHSCOPE_API_KEY 传入）
QWEN_API_KEY = os.environ.get("DASHSCOPE_API_KEY", "")
# 模型名：qwen-plus / qwen-turbo / qwen-max
QWEN_MODEL = "qwen-plus"
# 关键词置信度阈值：低于该值的关键词不写入 keywords.json
KEYWORD_CONFIDENCE_THRESHOLD = 0.95
# 关键词最多保留数量
MAX_KEYWORDS = 20
# 兜底数量：若没有关键词达到置信度阈值，则取置信度最高的前 N 个
KEYWORD_FALLBACK_COUNT = 3

# ============ 网站检索 ============
# YouTube 标题屏蔽词：标题含任一词汇的视频直接不提取
YOUTUBE_BLOCK_WORDS = [
    "习近平", "国家领导人", "中国", "中央","習近平","彭麗媛","红卫兵",
    "共产党","共產黨","紅衛兵","中华民国","中華民國","中國","彭丽媛"
]
# 每个关键词在每个网站抓取的条数
SEARCH_LIMIT = 10
# 最终报告展示的最相关条目数
TOP_N = 10
# 网站权重：YouTube / Bilibili 优先，Bing 次之
SOURCE_WEIGHT = {
    "youtube": 1.0,
    "bilibili": 1.0,
    "bing": 0.8,
}


def ensure_dirs():
    """确保工作目录存在。"""
    for d in (DATA_DIR, KEYFRAME_DIR, AUDIO_DIR, OUTPUT_DIR, RESULTS_DIR):
        d.mkdir(parents=True, exist_ok=True)
