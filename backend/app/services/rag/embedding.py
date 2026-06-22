"""
Embedding服务

支持多种Embedding模型的文本向量化
"""

from typing import List, Optional, Dict, Any
from dataclasses import dataclass
import numpy as np


@dataclass
class EmbeddingResult:
    """Embedding结果"""
    text: str
    embedding: List[float]
    model: str
    token_count: int
    backend: str = ""
    degraded: bool = False
    degraded_reason: str = ""


class EmbeddingService:
    """Embedding服务"""

    def __init__(
        self,
        model_name: str = "bge-large-zh",
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        batch_size: int = 32,
        max_retries: int = 3
    ):
        self.model_name = model_name
        self.api_key = api_key
        self.api_base = api_base
        self.batch_size = batch_size
        self.max_retries = max_retries

        self.default_backend = "unknown"
        self.last_backend = "unknown"
        self.last_degraded = False
        self.last_degraded_reason = ""

        # 根据模型名称选择实现
        if model_name.startswith("bge"):
            self._init_bge_model()
        elif model_name.startswith("text-embedding") or model_name.startswith("deepseek"):
            self._init_api_model()
        else:
            self._init_local_model()

    def _init_bge_model(self):
        """初始化BGE模型"""
        try:
            from sentence_transformers import SentenceTransformer

            model_map = {
                "bge-large-zh": "BAAI/bge-large-zh-v1.5",
                "bge-large-zh-v1.5": "BAAI/bge-large-zh-v1.5",
                "bge-base-zh": "BAAI/bge-base-zh-v1.5",
                "bge-base-zh-v1.5": "BAAI/bge-base-zh-v1.5",
                "bge-small-zh": "BAAI/bge-small-zh-v1.5",
                "bge-small-zh-v1.5": "BAAI/bge-small-zh-v1.5",
                "bge-large-en": "BAAI/bge-large-en-v1.5",
                "bge-base-en": "BAAI/bge-base-en-v1.5"
            }

            actual_model = model_map.get(self.model_name, self.model_name)
            print(f"Loading embedding model: {actual_model}")
            self.model = SentenceTransformer(actual_model)
            self.use_api = False
            self.default_backend = "local_model"
            self.last_backend = self.default_backend
            self.last_degraded = False
            self.last_degraded_reason = ""
            try:
                self.dimension = self.model.get_embedding_dimension()
            except AttributeError:
                self.dimension = self.model.get_sentence_embedding_dimension()

        except ImportError:
            print("警告: sentence_transformers未安装，将回退到API Embedding")
            self._init_api_model()

    def _init_api_model(self):
        """初始化API模型（DeepSeek/OpenAI兼容）"""
        self.model = None
        self.use_api = True
        self.default_backend = "api"
        self.last_backend = self.default_backend
        self.last_degraded = False
        self.last_degraded_reason = ""
        # DeepSeek embedding 输出维度，默认使用 1024
        self.dimension = 1024

    def _init_local_model(self):
        """初始化本地模型"""
        self.model = None
        self.use_api = False
        self.default_backend = "local_fallback"
        self.last_backend = self.default_backend
        self.last_degraded = False
        self.last_degraded_reason = ""
        self.dimension = 768

    def embed_text(self, text: str) -> EmbeddingResult:
        """
        生成单个文本的Embedding

        Args:
            text: 输入文本

        Returns:
            Embedding结果
        """
        processed_text = self._preprocess_text(text)
        token_count = self._estimate_token_count(processed_text)
        self.last_backend = self.default_backend
        self.last_degraded = False
        self.last_degraded_reason = ""

        if self.use_api:
            embedding = self._embed_with_api(processed_text)
        elif self.model is not None:
            embedding = self._embed_with_model(processed_text)
        else:
            embedding = self._embed_with_api(processed_text)

        return EmbeddingResult(
            text=text,
            embedding=embedding,
            model=self.model_name,
            token_count=token_count,
            backend=self.last_backend,
            degraded=self.last_degraded,
            degraded_reason=self.last_degraded_reason,
        )

    def embed_batch(self, texts: List[str]) -> List[EmbeddingResult]:
        """
        批量生成Embedding

        Args:
            texts: 文本列表

        Returns:
            Embedding结果列表
        """
        results = []

        for i in range(0, len(texts), self.batch_size):
            batch = texts[i:i + self.batch_size]
            batch_results = self._embed_batch_internal(batch)
            results.extend(batch_results)

        return results

    def _embed_batch_internal(self, texts: List[str]) -> List[EmbeddingResult]:
        """内部批量处理"""
        processed_texts = [self._preprocess_text(t) for t in texts]
        token_counts = [self._estimate_token_count(t) for t in processed_texts]

        if self.use_api:
            embeddings = [self._embed_with_api(t) for t in processed_texts]
        elif self.model is not None:
            embeddings = self._embed_with_model_batch(processed_texts)
        else:
            embeddings = [self._embed_with_api(t) for t in processed_texts]

        results = []
        for i, (text, embedding, token_count) in enumerate(zip(texts, embeddings, token_counts)):
            results.append(EmbeddingResult(
                text=text,
                embedding=embedding,
                model=self.model_name,
                token_count=token_count
            ))

        return results

    def _preprocess_text(self, text: str) -> str:
        """预处理文本"""
        text = ' '.join(text.split())
        max_length = 512
        if len(text) > max_length * 4:
            text = text[:max_length * 4]
        return text

    def _estimate_token_count(self, text: str) -> int:
        """估算token数量"""
        chinese_chars = sum(1 for c in text if '一' <= c <= '鿿')
        other_chars = len(text) - chinese_chars
        return int(chinese_chars / 1.5 + other_chars / 4)

    def _embed_with_model(self, text: str) -> List[float]:
        """使用本地模型生成Embedding"""
        try:
            embedding = self.model.encode(text, normalize_embeddings=True)
            self.last_backend = "local_model"
            self.last_degraded = False
            self.last_degraded_reason = ""
            return embedding.tolist()
        except Exception as e:
            print(f"模型Embedding生成失败: {e}")
            self.last_degraded = True
            self.last_degraded_reason = str(e)
            return self._embed_with_api(text)

    def _embed_with_model_batch(self, texts: List[str]) -> List[List[float]]:
        """使用本地模型批量生成Embedding"""
        try:
            embeddings = self.model.encode(texts, normalize_embeddings=True, batch_size=self.batch_size)
            return [e.tolist() for e in embeddings]
        except Exception as e:
            print(f"批量Embedding生成失败: {e}")
            return [self._embed_with_api(t) for t in texts]

    def _embed_with_api(self, text: str) -> List[float]:
        """使用API生成Embedding（DeepSeek/OpenAI兼容）"""
        try:
            import openai

            client = openai.OpenAI(
                api_key=self.api_key or "dummy",
                base_url=self.api_base
            )

            # DeepSeek embedding 模型名
            embedding_model = "deepseek-embedding" if "deepseek" in (self.api_base or "").lower() else self.model_name

            response = client.embeddings.create(
                model=embedding_model,
                input=text
            )

            embedding = response.data[0].embedding
            self.last_backend = "api"
            self.last_degraded = False
            self.last_degraded_reason = ""
            # 更新实际维度
            self.dimension = len(embedding)
            return embedding

        except Exception as e:
            print(f"API Embedding生成失败: {e}")
            self.last_backend = "simplified_fallback"
            self.last_degraded = True
            self.last_degraded_reason = str(e)
            return self._embed_simplified(text)

    def _embed_simplified(self, text: str) -> List[float]:
        """
        简化Embedding实现

        使用哈希生成伪向量，仅用于降级回退
        """
        import hashlib

        hash_obj = hashlib.sha256(text.encode())
        hash_bytes = hash_obj.digest()

        embedding = []
        for i in range(0, len(hash_bytes), 4):
            if len(embedding) >= self.dimension:
                break
            chunk = hash_bytes[i:i + 4]
            if len(chunk) == 4:
                value = int.from_bytes(chunk, byteorder='big') / (2**32)
                embedding.append(value * 2 - 1)

        while len(embedding) < self.dimension:
            embedding.append(0.0)

        embedding = embedding[:self.dimension]

        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = (np.array(embedding) / norm).tolist()

        return embedding

    def similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """计算两个Embedding的余弦相似度"""
        vec1 = np.array(embedding1)
        vec2 = np.array(embedding2)

        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return float(dot_product / (norm1 * norm2))
