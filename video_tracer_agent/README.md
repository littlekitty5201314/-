# 视频溯源智能体使用说明

## 一、功能概述

给定一个视频文件，自动完成以下溯源流程：

1. **剪辑判断 + 关键帧提取**（ffmpeg）
   - 通过场景切换检测判断视频是否被剪辑
   - 按固定间隔 + 场景切换点抽取关键帧

2. **视频内容提取**（本地，不联网）
   - OCR：识别关键帧中的文字（RapidOCR）
   - ASR：语音转写（faster-whisper）

3. **关键词提取**（通义千问大模型）
   - 从 OCR+ASR 文本中提取关键词及置信度
   - 按置信度从高到低排序，**低于 0.95 的关键词不写入 keywords.json**
   - 若全部关键词都低于 0.95，则兜底取置信度最高的 3 个

4. **三网站检索**（YouTube / Bilibili / Bing）
   - 读取 keywords.json，逐一检索并保存结果

5. **相关性排序**
   - 根据网页标题与关键词的匹配度打分
   - **YouTube 与 Bilibili 优先**于 Bing
   - 选出最相关的 Top 10

6. **输出溯源报告**（Markdown）
   - 包含：关键词、网站、网站置信度

## 二、目录结构

```
video_tracer_agent/
├── main.py                # 主入口
├── config.py              # 全局配置
├── video_analyzer.py      # ffmpeg 剪辑判断 + 关键帧提取
├── ocr_engine.py          # 本地 OCR
├── asr_engine.py          # 本地 ASR
├── keyword_extractor.py   # 千问大模型关键词提取
├── search_aggregator.py   # 三网站检索 + 排序
├── report_generator.py    # 报告生成
├── crawlers/
│   ├── youtube_crawl.py   # YouTube 爬虫
│   ├── bilibili_crawl.py  # Bilibili 爬虫
│   └── bing_crawl.py      # Bing 爬虫
├── data/                  # 关键帧、音频等中间文件
├── results/               # 三网站抓取结果
├── output/                # 最终报告输出
└── keywords.json          # 关键词（自动生成）
```

## 三、环境准备（本机首次使用）

### 一键安装（推荐）

双击项目里的 **`setup.bat`**，它会自动完成：
1. 创建独立 Python 虚拟环境（`venv` 文件夹）
2. 安装全部依赖（OCR / ASR / 爬虫）
3. 下载无头浏览器（YouTube/Bilibili 抓取用）
4. 检查 ffmpeg
5. 提示你填入千问 API Key

### 手动准备

1. 安装 Python 3.10+（勾选 "Add to PATH"）
2. 安装 ffmpeg 并把 `bin` 目录加入 PATH，验证 `ffmpeg -version`
3. 配置千问 API Key：`setx DASHSCOPE_API_KEY "sk-你的key"`

## 四、使用方法

### 视频放哪里？

**视频不用放进项目文件夹**，放在电脑任意位置都行（桌面、下载目录、U 盘等）。
运行时把视频的完整路径告诉程序即可。

### 方式一：一键启动脚本（推荐，最简单）

1. 找到项目里的 `run.bat` 文件
2. **把视频文件直接拖到 `run.bat` 图标上**，松手即可自动运行
3. 或者双击 `run.bat`，按提示输入视频完整路径

### 方式二：命令行

```bash
# 先 cd 到项目目录，再用项目内的虚拟环境运行
venv\Scripts\python.exe main.py "C:/你的视频路径/video.mp4"
```

运行完成后：
- `keywords.json` — 关键词（按置信度降序）
- `output/keywords_with_confidence.json` — 带置信度的关键词
- `output/溯源报告.md` — 最终溯源报告

## 五、移植到另一台电脑

整个文件夹可以打包带走，目标电脑需满足：

| 前置条件 | 说明 |
| --- | --- |
| Windows 系统 | 脚本按 Windows 设计 |
| Python 3.10+ | 需勾选 "Add to PATH" |
| ffmpeg | 需加入 PATH |
| 网络 | 需能访问国内镜像（装依赖、下模型）、千问 API、三个网站 |

**移植步骤：**
1. 把整个 `video_tracer_agent` 文件夹（**不要**带 `venv` 文件夹和 `data/`、`output/`、`results/`，这些是本地生成的；带上反而可能因为旧路径出错）
2. 双击 `setup.bat` → 自动装环境、装依赖、下浏览器
3. 填入千问 API Key
4. 把视频拖到 `run.bat` 上运行

> 首次运行 ASR 时，会自动从国内镜像下载 whisper 模型（约几百 MB，仅第一次）。

## 六、可调参数（config.py）

| 参数 | 说明 | 默认值 |
| --- | --- | --- |
| KEYFRAME_INTERVAL | 关键帧间隔（秒） | 2 |
| SCENE_THRESHOLD | 场景切换阈值 | 0.35 |
| KEYWORD_CONFIDENCE_THRESHOLD | 关键词置信度下限 | 0.95 |
| TOP_N | 报告展示条数 | 10 |
| ASR_MODEL_SIZE | 语音模型大小 | small |
