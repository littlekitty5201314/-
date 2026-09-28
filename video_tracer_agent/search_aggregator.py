# -*- coding: utf-8 -*-
"""
视频溯源智能体 —— 网站检索汇总模块

调用三个爬虫，汇总结果并按"标题相关性 + 网站权重"排序，
选出最相关的 TOP N 内容（YouTube / Bilibili 优先）。
"""
import json
from pathlib import Path

import config

SOURCE_NAMES = {
    "youtube": "YouTube",
    "bilibili": "Bilibili",
    "bing": "Bing",
}


def _tokenize(text: str) -> set:
    """简单分词：中文按字、英文按词。"""
    import re
    tokens = set()
    for word in re.findall(r"[a-zA-Z0-9]+", text.lower()):
        tokens.add(word)
    for ch in text:
        if "\u4e00" <= ch <= "\u9fff":
            tokens.add(ch)
    return tokens


def score_title(title: str, keywords_with_conf: dict) -> dict:
    """
    计算单个标题与所有关键词的匹配度。

    返回：{score: float, matched: [str]}
    """
    title_tokens = _tokenize(title)
    if not title_tokens:
        return {"score": 0.0, "matched": []}

    matched = []
    best = 0.0
    for kw, conf in keywords_with_conf.items():
        kw_tokens = _tokenize(kw)
        if not kw_tokens:
            continue
        overlap = len(title_tokens & kw_tokens)
        if overlap == 0:
            continue
        # 关键词覆盖度 × 关键词置信度，取最强匹配
        coverage = overlap / len(kw_tokens)
        s = coverage * conf
        if s > best:
            best = s
        matched.append(kw)

    return {"score": round(best, 4), "matched": matched}


def rank_results(all_results: list, keywords_with_conf: dict, top_n: int = None) -> list:
    """
    对抓取结果排序。

    规则：
    1. 按标题与关键词的匹配分从高到低
    2. 同分时按网站权重（YouTube/Bilibili > Bing）优先
    """
    top_n = top_n or config.TOP_N
    scored = []
    for item in all_results:
        s = score_title(item.get("title", ""), keywords_with_conf)
        source_weight = config.SOURCE_WEIGHT.get(item.get("source", "bing"), 0.8)
        final_score = s["score"] * source_weight
        scored.append({
            **item,
            "matched_keywords": s["matched"],
            "title_score": s["score"],
            "final_score": round(final_score, 4),
        })

    # 先按 final_score 降序；同分时 YouTube/Bilibili 排在 Bing 前
    def sort_key(x):
        is_video = 0 if x.get("source") in ("youtube", "bilibili") else 1
        return (-x["final_score"], is_video, -x.get("title_score", 0))

    scored.sort(key=sort_key)
    return scored[:top_n]


def load_results_dir() -> list:
    """读取 results 目录下三个网站的抓取结果。"""
    all_results = []
    for name in ("youtube", "bilibili", "bing"):
        p = config.RESULTS_DIR / f"{name}_results.json"
        if not p.exists():
            continue
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            if isinstance(data, list):
                all_results.extend(data)
        except json.JSONDecodeError:
            print(f"警告：{p} 不是有效 JSON，已跳过")
    return all_results


def search_and_rank(keywords_with_conf: dict, top_n: int = None) -> list:
    """完整流程：抓取 → 汇总 → 排序。"""
    from crawlers import youtube_crawl, bilibili_crawl, bing_crawl

    keywords = list(keywords_with_conf.keys())
    print(f"开始检索 {len(keywords)} 个关键词...")

    config.ensure_dirs()
    yt = youtube_crawl.run(keywords, limit=config.SEARCH_LIMIT)
    bl = bilibili_crawl.run(keywords, limit=config.SEARCH_LIMIT)
    bing = bing_crawl.run(keywords, limit=config.SEARCH_LIMIT)

    all_results = yt + bl + bing
    print(f"共获取 {len(all_results)} 条结果，开始排序...")
    return rank_results(all_results, keywords_with_conf, top_n=top_n)
