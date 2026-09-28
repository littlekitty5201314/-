# -*- coding: utf-8 -*-
"""
视频溯源智能体 —— OCR 模块（本地识别关键帧文字）

支持多种引擎，按配置自动选择，无需联网。
"""
from pathlib import Path

import config

_OCR = None
_OCR_ENGINE = None


def _load_engine():
    """懒加载 OCR 引擎。"""
    global _OCR, _OCR_ENGINE
    engine = config.OCR_ENGINE.lower()

    if engine == "rapidocr":
        try:
            from rapidocr_onnxruntime import RapidOCR
            _OCR = RapidOCR()
            _OCR_ENGINE = "rapidocr"
            return _OCR
        except ImportError:
            raise RuntimeError(
                "未安装 rapidocr_onnxruntime，请运行：\n"
                "  pip install rapidocr-onnxruntime"
            )

    if engine == "easyocr":
        try:
            import easyocr
            _OCR = easyocr.Reader(["ch_sim", "en"], gpu=False)
            _OCR_ENGINE = "easyocr"
            return _OCR
        except ImportError:
            raise RuntimeError("未安装 easyocr，请运行：pip install easyocr")

    if engine == "tesseract":
        try:
            import pytesseract
            _OCR = pytesseract
            _OCR_ENGINE = "tesseract"
            return _OCR
        except ImportError:
            raise RuntimeError(
                "未安装 pytesseract，请运行：pip install pytesseract "
                "并安装 Tesseract 程序"
            )

    raise RuntimeError(f"未知 OCR 引擎：{config.OCR_ENGINE}")


def ocr_image(image_path: Path) -> str:
    """识别单张图片中的文字，返回文本。"""
    _load_engine()

    if _OCR_ENGINE == "rapidocr":
        result, _ = _OCR(str(image_path))
        if not result:
            return ""
        return "\n".join(line[1] for line in result)

    if _OCR_ENGINE == "easyocr":
        result = _OCR.readtext(str(image_path), detail=0, paragraph=True)
        return "\n".join(result)

    if _OCR_ENGINE == "tesseract":
        from PIL import Image
        return _OCR.image_to_string(Image.open(image_path), lang="chi_sim+eng")

    return ""


def ocr_keyframes(keyframe_paths: list) -> dict:
    """
    批量识别关键帧。

    返回：{帧文件路径: 识别文本}
    """
    results = {}
    for p in keyframe_paths:
        path = Path(p)
        if not path.exists():
            continue
        try:
            text = ocr_image(path).strip()
        except Exception as e:
            text = f"[OCR失败] {e}"
        results[str(path)] = text
    return results


def ocr_to_text(keyframe_paths: list) -> str:
    """把关键帧 OCR 结果合并成一段文本。"""
    results = ocr_keyframes(keyframe_paths)
    lines = []
    for path, text in results.items():
        if text and not text.startswith("[OCR失败]"):
            lines.append(text)
    return "\n".join(lines)
