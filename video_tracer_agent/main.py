# -*- coding: utf-8 -*-
"""
视频溯源智能体 —— 主流程入口

用法：
    python main.py <视频路径>

流程：
    1. ffmpeg 判断是否剪辑 + 提取关键帧
    2. 本地 OCR（关键帧文字）+ 本地 ASR（语音转写）
    3. 千问大模型提取关键词（按置信度降序，低于阈值丢弃）
    4. 三网站（YouTube / Bilibili / Bing）抓取相关数据
    5. 按标题相关性排序，选出 Top N（YouTube/Bilibili 优先）
    6. 输出溯源报告
"""
import sys
from pathlib import Path

import config


def main():
    if len(sys.argv) < 2:
        print("用法：python main.py <视频路径>")
        print("示例：python main.py C:/videos/test.mp4")
        sys.exit(1)

    video_path = Path(sys.argv[1])
    if not video_path.exists():
        print(f"错误：视频文件不存在：{video_path}")
        sys.exit(1)

    config.ensure_dirs()

    # ===== 1. 视频分析 =====
    print("=" * 60)
    print("[1/6] 视频分析（ffmpeg）...")
    import video_analyzer
    info = video_analyzer.analyze(video_path)
    edit_result = {
        "edited": info["edited"],
        "cut_count": info["cut_count"],
        "confidence": info["confidence"],
        "density_per_min": info["density_per_min"],
    }
    print(f"  时长 {info['duration']:.1f}s | 剪辑判断："
          f"{'是' if info['edited'] else '否'}（置信度 {info['confidence']:.2f}）")
    print(f"  已提取 {info['keyframe_count']} 个关键帧")

    # ===== 2. OCR + ASR =====
    print("[2/6] 视频内容提取（本地 OCR + ASR）...")
    import ocr_engine
    ocr_text = ocr_engine.ocr_to_text(info["keyframes"])
    print(f"  OCR 提取文字 {len(ocr_text)} 字")

    import asr_engine
    asr_text = asr_engine.transcribe(video_path)
    print(f"  ASR 转写文字 {len(asr_text)} 字")

    combined_text = f"【画面文字(OCR)】\n{ocr_text}\n\n【语音内容(ASR)】\n{asr_text}"
    if not ocr_text.strip() and not asr_text.strip():
        print("警告：OCR 与 ASR 均未提取到内容，仍将尝试用文件名生成关键词。")
        combined_text = video_path.stem

    # ===== 3. 关键词提取 =====
    print("[3/6] 千问大模型提取关键词...")
    import keyword_extractor
    keywords = keyword_extractor.extract_keywords(combined_text)
    if not keywords:
        print(f"  未提取到置信度 ≥ {config.KEYWORD_CONFIDENCE_THRESHOLD} 的关键词，流程终止。")
        sys.exit(1)
    keyword_extractor.save_keywords(keywords)
    print(f"  提取到 {len(keywords)} 个关键词：")
    for k in keywords:
        print(f"    - {k['keyword']} ({k['confidence']:.2f})")

    # ===== 4+5. 检索 + 排序 =====
    print("[4/6] 三网站检索...")
    import search_aggregator
    kw_conf = {k["keyword"]: k["confidence"] for k in keywords}
    top_results = search_aggregator.search_and_rank(kw_conf, top_n=config.TOP_N)

    print("[5/6] 排序完成，Top {}：".format(len(top_results)))
    for i, r in enumerate(top_results, 1):
        src = search_aggregator.SOURCE_NAMES.get(r["source"], r["source"])
        print(f"  {i}. [{src}] {r['title'][:40]} (置信度 {r['final_score']:.2f})")

    # ===== 6. 报告 =====
    print("[6/6] 生成报告...")
    import report_generator
    report_path = report_generator.save_report(info, edit_result, keywords, top_results)
    print("=" * 60)
    print(f"完成！报告已保存到：{report_path}")


if __name__ == "__main__":
    main()
