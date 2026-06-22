"""
LLM 视觉识别服务

使用 DeepSeek/Mimo 多模态模型识别图片中的文字，作为 OCR 的降级方案。
"""

import base64
from typing import Dict, Any
from loguru import logger


async def recognize_with_llm(
    image_bytes: bytes,
    api_key: str,
    base_url: str = "https://api.deepseek.com",
    model: str = "deepseek-chat",
) -> Dict[str, Any]:
    """
    使用 LLM 多模态能力识别图片中的文字

    Args:
        image_bytes: 图片二进制数据
        api_key: API Key
        base_url: API 地址
        model: 模型名称

    Returns:
        { text: str, confidence: float, engine: str }
    """
    try:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        image_base64 = base64.b64encode(image_bytes).decode("utf-8")

        # 检测图片格式
        fmt = "jpeg"
        if image_bytes[:4] == b'\x89PNG':
            fmt = "png"
        elif image_bytes[:4] == b'RIFF':
            fmt = "webp"

        response = await client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "请识别这张图片中的所有文字内容。只输出识别到的文字，保持原始段落格式，不要添加任何解释或说明。如果图片中没有文字，请输出"无文字内容"。",
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/{fmt};base64,{image_base64}",
                            },
                        },
                    ],
                }
            ],
            max_tokens=4000,
        )

        text = response.choices[0].message.content or ""
        text = text.strip()

        if text == "无文字内容":
            return {"text": "", "confidence": 0, "engine": "llm", "error": "图片中未检测到文字"}

        return {
            "text": text,
            "confidence": 0.7,  # LLM 识别置信度默认中等
            "engine": "llm",
        }

    except Exception as e:
        logger.error(f"LLM 视觉识别失败: {e}")
        return {"text": "", "confidence": 0, "engine": "llm", "error": "LLM 识别服务异常，请稍后重试"}
