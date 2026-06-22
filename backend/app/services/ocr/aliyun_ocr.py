"""
阿里云 OCR 文字识别服务

使用阿里云通用文字识别 API，支持中英文混合识别。
"""

import base64
import threading
from typing import Dict, Any
from loguru import logger


class AliyunOCR:
    """阿里云通用文字识别"""

    def __init__(self, access_key_id: str, access_key_secret: str, endpoint: str = "ocr-api.cn-hangzhou.aliyuncs.com"):
        self.access_key_id = access_key_id
        self.access_key_secret = access_key_secret
        self.endpoint = endpoint
        self._client = None
        self._lock = threading.Lock()

    def _get_client(self):
        if self._client is None:
            with self._lock:
                # Double-checked locking
                if self._client is None:
                    from alibabacloud_ocr_api20210707.client import Client
                    from alibabacloud_tea_openapi import models as open_api_models

                    config = open_api_models.Config(
                        access_key_id=self.access_key_id,
                        access_key_secret=self.access_key_secret,
                    )
                    config.endpoint = self.endpoint
                    self._client = Client(config)
        return self._client

    def recognize(self, image_bytes: bytes) -> Dict[str, Any]:
        """
        识别图片中的文字

        Args:
            image_bytes: 图片二进制数据

        Returns:
            { text: str, confidence: float, engine: str }
        """
        try:
            from alibabacloud_ocr_api20210707 import models as ocr_models

            client = self._get_client()
            body_stream = base64.b64encode(image_bytes).decode("utf-8")

            request = ocr_models.RecognizeGeneralRequest(body=body_stream)
            response = client.recognize_general(request)
            body = response.body

            if body.code and body.code != "200":
                logger.warning(f"阿里云 OCR 返回错误: {body.code} - {body.message}")
                return {"text": "", "confidence": 0, "engine": "aliyun", "error": body.message}

            # 提取识别文本
            data = body.data or ""
            text = data if isinstance(data, str) else str(data)

            return {
                "text": text.strip(),
                "confidence": 0.9,  # 阿里云通用接口不返回置信度，默认高置信
                "engine": "aliyun",
            }

        except ImportError:
            logger.error("阿里云 OCR SDK 未安装，请执行: pip install alibabacloud-ocr-api20210707")
            return {"text": "", "confidence": 0, "engine": "aliyun", "error": "SDK 未安装"}
        except Exception as e:
            logger.error(f"阿里云 OCR 识别失败: {e}")
            return {"text": "", "confidence": 0, "engine": "aliyun", "error": "阿里云 OCR 服务异常，请稍后重试"}
