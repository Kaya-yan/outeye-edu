"""
OCR 文字识别服务

支持阿里云 OCR 和 LLM 视觉两种识别引擎。
"""

from app.services.ocr.aliyun_ocr import AliyunOCR
from app.services.ocr.llm_vision import recognize_with_llm

__all__ = ["AliyunOCR", "recognize_with_llm"]
