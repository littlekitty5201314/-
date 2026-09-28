# -*- coding: utf-8 -*-
"""
视频溯源智能体

给定一个视频，通过 ffmpeg 判断剪辑、提取关键帧，本地 OCR/ASR 提取内容，
千问大模型提取关键词，再在 YouTube / Bilibili / Bing 检索最相关来源，输出溯源报告。

依赖安装（推荐直接运行 setup.bat 自动完成）：
    pip install -r requirements.txt

系统依赖：
    - ffmpeg（需加入 PATH）

千问 API Key（二选一）：
    - 环境变量：set DASHSCOPE_API_KEY=sk-xxx
    - 或修改 config.py 中的 QWEN_API_KEY

用法：
    python main.py <视频路径>
"""
