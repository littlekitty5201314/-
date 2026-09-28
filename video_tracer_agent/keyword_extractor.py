# -*- coding: utf-8 -*-
"""
视频溯源智能体 —— 千问大模型关键词提取模块

把 OCR + ASR 得到的视频文本送入通义千问，
提取关键词及其置信度，按置信度降序写入 keywords.json
（低于阈值 0.95 的丢弃；若全部低于阈值，则兜底取置信度最高的前 3 个）。
"""
import json
import re
from pathlib import Path

import config

_PROMPT = """你是视频内容分析专家。下面是一段视频经过 OCR（画面文字识别）和 ASR（语音转写）得到的文本。

请完成以下任务：
1. 提取最能代表该视频主题与内容的关键词（包括人物、事件、专有名词、主题短语等）。
2. 为每个关键词给出置信度 confidence（0~1 的小数），表示该关键词与视频内容的相关程度。
3. 严格只输出 JSON 数组，格式如下，不要输出任何其他文字或解释：
[
  {"keyword": "关键词1", "confidence": 0.95},
  {"keyword": "关键词2", "confidence": 0.83}
]

视频文本内容如下：
{text}
"""


def _call_qwen(text: str) -> str:
    """调用通义千问 OpenAI 兼容接口。"""
    import urllib.request

    api_key = config.QWEN_API_KEY
    if not api_key:
        raise RuntimeError(
            "未配置通义千问 API Key，请设置环境变量 DASHSCOPE_API_KEY，"
            "或在 config.py 中填写 QWEN_API_KEY"
        )

    url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
    payload = {
        "model": config.QWEN_MODEL,
        "messages": [
            {"role": "system", "content": "你是专业的视频内容分析助手。"},
            {"role": "user", "content": _PROMPT.replace("{text}", text)},
        ],
        "temperature": 0.2,
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data["choices"][0]["message"]["content"]


def extract_keywords(text: str) -> list:
    """
    从文本中提取关键词及置信度。

    返回：[{"keyword": str, "confidence": float}, ...]（已降序、已过滤）
    """
    if not text or not text.strip():
        return []

    raw = _call_qwen(text.strip())

    # 稳健解析：截取第一个 [ 到最后一个 ] 之间的 JSON
    match = re.search(r"\[.*\]", raw, re.DOTALL)
    if not match:
        raise RuntimeError(f"大模型返回内容无法解析：{raw[:200]}")
    try:
        items = json.loads(match.group(0))
    except json.JSONDecodeError:
        raise RuntimeError(f"大模型返回的 JSON 格式错误：{raw[:200]}")

    keywords = []
    for it in items:
        kw = str(it.get("keyword", "")).strip()
        if not kw:
            continue
        try:
            conf = float(it.get("confidence", 0))
        except (TypeError, ValueError):
            conf = 0.0
        conf = max(0.0, min(1.0, conf))
        keywords.append({"keyword": kw, "confidence": round(conf, 4)})

    # 去重（保留置信度最高者）并按置信度降序
    seen = {}
    for k in keywords:
        if k["keyword"] not in seen or k["confidence"] > seen[k["keyword"]]["confidence"]:
            seen[k["keyword"]] = k
    keywords = list(seen.values())
    keywords.sort(key=lambda x: x["confidence"], reverse=True)

    # 置信度过滤：只保留 >= 阈值的；若一个都没达标，则兜底取置信度最高的前 N 个
    filtered = [k for k in keywords if k["confidence"] >= config.KEYWORD_CONFIDENCE_THRESHOLD]
    if not filtered:
        filtered = keywords[: config.KEYWORD_FALLBACK_COUNT]

    return filtered[: config.MAX_KEYWORDS]


def save_keywords(keywords: list) -> Path:
    """把关键词写入 keywords.json（数组格式，兼容爬虫脚本）。"""
    # 写入纯关键词数组，供爬虫脚本读取
    keyword_list = [k["keyword"] for k in keywords]
    config.KEYWORDS_FILE.write_text(
        json.dumps(keyword_list, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    # 同时保存带置信度的完整版
    detail_file = config.OUTPUT_DIR / "keywords_with_confidence.json"
    config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    detail_file.write_text(
        json.dumps(keywords, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return config.KEYWORDS_FILE
