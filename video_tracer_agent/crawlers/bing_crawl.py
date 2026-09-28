# -*- coding: utf-8 -*-
"""
Bing 搜索爬虫（源自用户提供的 bing_crawl.py，已整合为可复用函数）。

注意：原脚本把"保存结果"的代码写在了 if __name__ == "__main__" 之外
导致 import 时会误执行，此处已修复。

依赖：scrapling
"""
import time
from pathlib import Path
from urllib.parse import urlencode, urljoin, urldefrag, urlparse

import config

KEYWORDS_FILE = config.KEYWORDS_FILE
RESULTS_FILE = config.RESULTS_DIR / "bing_results.json"


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
    if raw_url.lower().startswith(("javascript:", "mailto:", "tel:", "#")):
        return None
    full_url = urljoin(base_url, raw_url)
    full_url, _ = urldefrag(full_url)
    parsed = urlparse(full_url)
    if parsed.scheme.lower() not in ("http", "https"):
        return None
    if not parsed.netloc:
        return None
    return full_url


def is_valid_result_url(url):
    if not url:
        return False
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    blocked_hosts = ("bing.com", "microsoft.com", "msn.com")
    if any(host == b or host.endswith("." + b) for b in blocked_hosts):
        return False
    blocked_extensions = (
        ".jpg", ".jpeg", ".png", ".gif", ".svg", ".pdf", ".zip", ".mp4", ".mp3",
    )
    if parsed.path.lower().endswith(blocked_extensions):
        return False
    return True


def search_bing(keyword, limit=10):
    """使用 Bing 搜索关键词，返回前 limit 条结果。"""
    from scrapling.fetchers import Fetcher

    search_url = "https://cn.bing.com/search?" + urlencode({"q": keyword})
    try:
        page = Fetcher.get(search_url, timeout=30, impersonate="chrome")
    except Exception as exc:
        print(f"Bing 请求失败：{type(exc).__name__}: {exc}")
        return []

    selectors = ["li.b_algo h2 a", "#b_results h2 a", "main h2 a", "h2 a"]
    links = []
    for selector in selectors:
        cur = page.css(selector)
        if cur:
            links = cur
            break
    if not links:
        print("没有找到搜索结果。")
        return []

    results = []
    seen_urls = set()
    for link in links:
        title = " ".join(
            p.strip() for p in link.css("::text").getall() if p.strip()
        )
        result_url = normalize_url(link.attrib.get("href", ""), page.url)
        if not title or not result_url or not is_valid_result_url(result_url):
            continue
        url_key = result_url.rstrip("/").lower()
        if url_key in seen_urls:
            continue
        seen_urls.add(url_key)
        results.append({
            "rank": len(results) + 1,
            "source": "bing",
            "keyword": keyword,
            "title": title,
            "url": result_url,
        })
        if len(results) >= limit:
            break
    return results


def run(keywords, limit=10):
    all_results = []
    for i, kw in enumerate(keywords, 1):
        print(f"[{i}/{len(keywords)}] Bing 搜索：{kw}")
        res = search_bing(kw, limit=limit)
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
