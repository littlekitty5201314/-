# -*- coding: utf-8 -*-
"""
Bilibili 搜索爬虫（源自用户提供的 bilibili_crawl.py，已整合为可复用函数）。

依赖：scrapling
"""
import time
from pathlib import Path
from urllib.parse import urlencode, urljoin, urldefrag

import config

KEYWORDS_FILE = config.KEYWORDS_FILE
RESULTS_FILE = config.RESULTS_DIR / "bilibili_results.json"


def load_keywords():
    import json
    if not KEYWORDS_FILE.exists():
        raise FileNotFoundError(f"找不到文件：{KEYWORDS_FILE}")
    with KEYWORDS_FILE.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict):
        data = data.get("keywords", [])
    keywords = []
    for item in data:
        if isinstance(item, str) and item.strip() and item.strip() not in keywords:
            keywords.append(item.strip())
    return keywords


def normalize_url(raw_url, base_url):
    if not raw_url:
        return None
    raw_url = raw_url.strip()
    if raw_url.startswith(("javascript:", "mailto:", "tel:", "#")):
        return None
    full_url = urljoin(base_url, raw_url)
    full_url, _ = urldefrag(full_url)
    if not full_url.startswith(("http://", "https://")):
        return None
    return full_url


def extract_title(item, link):
    title_selectors = [
        ".bili-video-card__info--tit",
        ".title",
        "h3",
        "a[title]",
    ]
    for selector in title_selectors:
        elements = item.css(selector)
        if not elements:
            continue
        el = elements[0]
        title = el.attrib.get("title", "").strip()
        if not title:
            title = " ".join(el.css("::text").getall()).strip()
        if title:
            return title
    title = link.attrib.get("title", "").strip()
    if not title:
        title = " ".join(link.css("::text").getall()).strip()
    return title


def search_bilibili(keyword, limit=10):
    """搜索 B 站并返回前 limit 个视频。"""
    from scrapling.fetchers import DynamicFetcher

    search_url = "https://search.bilibili.com/all?" + urlencode(
        {"keyword": keyword}
    )
    try:
        page = DynamicFetcher.fetch(
            search_url, headless=True, wait=5000, timeout=60000,
        )
    except Exception as exc:
        print(f"B站请求失败：{type(exc).__name__}: {exc}")
        return []

    item_selectors = [
        "li.video-list-item",
        "div.bili-video-card",
        "div.video-list-item",
    ]
    video_items = []
    for selector in item_selectors:
        items = page.css(selector)
        if items:
            video_items = items
            break
    if not video_items:
        video_items = page.css('a[href*="/video/"]')
    if not video_items:
        print("没有找到 B 站视频结果。")
        return []

    results = []
    seen_urls = set()
    for item in video_items:
        links = item.css('a[href*="/video/"]')
        if not links:
            href = item.attrib.get("href", "")
            if "/video/" in href:
                links = [item]
        if not links:
            continue
        link = links[0]
        video_url = normalize_url(
            link.attrib.get("href", ""), "https://www.bilibili.com"
        )
        if not video_url or "/video/" not in video_url:
            continue
        video_url = video_url.split("?")[0]
        url_key = video_url.rstrip("/").lower()
        if url_key in seen_urls:
            continue
        seen_urls.add(url_key)

        title = extract_title(item, link)
        if not title:
            continue
        results.append({
            "rank": len(results) + 1,
            "source": "bilibili",
            "keyword": keyword,
            "title": title,
            "url": video_url,
        })
        if len(results) >= limit:
            break
    return results


def run(keywords, limit=10):
    all_results = []
    for i, kw in enumerate(keywords, 1):
        print(f"[{i}/{len(keywords)}] Bilibili 搜索：{kw}")
        res = search_bilibili(kw, limit=limit)
        all_results.extend(res)
        time.sleep(2)
    RESULTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    import json
    RESULTS_FILE.write_text(
        json.dumps(all_results, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return all_results


if __name__ == "__main__":
    config.ensure_dirs()
    kws = load_keywords()
    run(kws, limit=config.SEARCH_LIMIT)
