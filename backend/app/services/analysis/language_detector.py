"""
语言检测模块

使用 langdetect 库自动识别文本语种，支持 55+ 种语言。
"""

from typing import Dict
from loguru import logger

# 项目支持的语言（外语教学常见语种）
SUPPORTED_LANGUAGES = {"en", "ja", "fr", "de", "es", "ko", "zh"}

# langdetect 语言代码 → 显示名称
LANG_NAMES = {
    "en": "英语", "ja": "日语", "fr": "法语", "de": "德语",
    "es": "西班牙语", "ko": "韩语", "zh": "中文", "ru": "俄语",
    "it": "意大利语", "pt": "葡萄牙语", "ar": "阿拉伯语",
}


class LanguageDetector:
    """语言检测器"""

    def detect(self, text: str) -> Dict[str, object]:
        """
        检测文本语言

        Returns:
            {"language": "en", "confidence": 0.95, "name": "英语"}
        """
        if not text or len(text.strip()) < 10:
            return {"language": "en", "confidence": 0.5, "name": "英语"}

        try:
            from langdetect import detect_langs

            results = detect_langs(text.strip())
            if not results:
                return {"language": "en", "confidence": 0.5, "name": "英语"}

            best = results[0]
            lang = best.lang
            confidence = best.prob

            # langdetect 的中文返回 "zh-cn" 或 "zh-tw"，统一为 "zh"
            if lang.startswith("zh"):
                lang = "zh"

            mapped_lang = lang if lang in SUPPORTED_LANGUAGES else "en"
            return {
                "language": mapped_lang,
                "confidence": round(confidence, 2),
                "name": LANG_NAMES.get(mapped_lang, mapped_lang),
            }
        except Exception as e:
            logger.warning(f"语言检测失败，默认英语: {e}")
            return {"language": "en", "confidence": 0.5, "name": "英语"}
