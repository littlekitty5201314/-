# -*- coding: utf-8 -*-
"""
视频溯源智能体 —— 报告生成模块

输出 Markdown 报告，包含：
- 视频基本信息与剪辑判断
- 关键词列表（按置信度降序）
- 最相关来源 Top N（网站 + 置信度）
"""
from datetime import datetime
from pathlib import Path

import config
from search_aggregator import SOURCE_NAMES


def build_report(video_info: dict, edit_result: dict, keywords: list,
                 top_results: list) -> str:
    """生成 Markdown 报告文本。"""
    lines = []
    lines.append("# 视频溯源报告")
    lines.append("")
    lines.append(f"> 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")

    # 视频信息
    lines.append("## 一、视频基本信息")
    lines.append("")
    lines.append("| 项目 | 内容 |")
    lines.append("| --- | --- |")
    lines.append(f"| 文件名 | {video_info.get('name', '')} |")
    lines.append(f"| 时长 | {video_info.get('duration', 0):.1f} 秒 |")
    lines.append(f"| 分辨率 | {video_info.get('width', '?')}x{video_info.get('height', '?')} |")
    lines.append(f"| 编码 | {video_info.get('codec', '?')} |")
    lines.append("")

    # 剪辑判断
    lines.append("## 二、剪辑判断")
    lines.append("")
    edited = edit_result.get("edited", False)
    lines.append(f"- **是否剪辑**：{'是（存在剪辑痕迹）' if edited else '否（无明显剪辑）'}")
    lines.append(f"- 场景切换次数：{edit_result.get('cut_count', 0)}")
    lines.append(f"- 剪辑判断置信度：{edit_result.get('confidence', 0):.2f}")
    lines.append(f"- 剪辑密度：{edit_result.get('density_per_min', 0):.2f} 次/分钟")
    lines.append("")

    # 关键词
    lines.append("## 三、关键词（按置信度降序）")
    lines.append("")
    lines.append("| 排名 | 关键词 | 置信度 |")
    lines.append("| --- | --- | --- |")
    for i, kw in enumerate(keywords, 1):
        lines.append(f"| {i} | {kw['keyword']} | {kw['confidence']:.2f} |")
    lines.append("")

    # 最相关来源
    lines.append("## 四、最相关来源 Top {}".format(len(top_results)))
    lines.append("")
    lines.append("| 排名 | 网站 | 标题 | 网站置信度 | 链接 |")
    lines.append("| --- | --- | --- | --- | --- |")
    for i, r in enumerate(top_results, 1):
        src = SOURCE_NAMES.get(r.get("source", "?"), r.get("source", "?"))
        title = r.get("title", "").replace("|", "\\|")
        url = r.get("url", "")
        conf = r.get("final_score", 0)
        lines.append(f"| {i} | {src} | {title} | {conf:.2f} | [{url}]({url}) |")
    lines.append("")

    lines.append("---")
    lines.append("*本报告由视频溯源智能体自动生成。*")
    return "\n".join(lines)


def save_report(video_info: dict, edit_result: dict, keywords: list,
                top_results: list) -> Path:
    """生成并保存报告，返回报告文件路径。"""
    config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    text = build_report(video_info, edit_result, keywords, top_results)
    config.REPORT_FILE.write_text(text, encoding="utf-8")
    return config.REPORT_FILE
