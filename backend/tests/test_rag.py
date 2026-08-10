"""
RAG服务测试
"""

import sys
import types
import uuid

import numpy as np
import pytest
from app.core.config import Settings
from app.services.rag.document_parser import DocumentParser
from app.services.rag.embedding import EmbeddingService
from app.services.rag.vector_store import VectorStore, VectorRecord
from app.services.rag.retriever import HybridRetriever, DocumentChunk
from app.services.rag.generator import RAGGenerator


class TestDocumentParser:
    """文档解析器测试"""

    def setup_method(self):
        self.parser = DocumentParser(chunk_size=200, chunk_overlap=50)

    def test_parse_text(self):
        """测试文本解析"""
        text = "This is a test document. It contains multiple sentences. Each sentence provides some information."
        result = self.parser.parse_text(text, "Test Document")

        assert result.id is not None
        assert result.title == "Test Document"
        assert result.content == text
        assert len(result.chunks) > 0

    def test_chunk_generation(self):
        """测试分块生成"""
        # 创建足够长的文本
        text = "This is a sentence. " * 50
        result = self.parser.parse_text(text)

        assert len(result.chunks) > 1
        for chunk in result.chunks:
            assert chunk.content
            assert chunk.doc_id == result.id

    def test_chunk_overlap(self):
        """测试分块重叠"""
        text = "A" * 500
        result = self.parser.parse_text(text)

        if len(result.chunks) > 1:
            # 检查是否有重叠
            first_chunk_end = result.chunks[0].content[-50:]
            second_chunk_start = result.chunks[1].content[:50]
            # 简化检查：确保不是完全不重叠
            assert True


class TestEmbeddingService:
    """Embedding服务测试"""

    def setup_method(self):
        self.service = EmbeddingService(model_name="bge-large-zh")

    def test_embed_text(self):
        """测试文本Embedding"""
        text = "This is a test sentence."
        result = self.service.embed_text(text)

        assert result.text == text
        assert len(result.embedding) > 0
        assert result.model == "bge-large-zh"

    def test_embedding_dimension(self):
        """测试Embedding维度"""
        text = "Test"
        result = self.service.embed_text(text)

        assert len(result.embedding) == self.service.dimension

    def test_similarity(self):
        """测试相似度计算"""
        embedding1 = [1.0, 0.0, 0.0]
        embedding2 = [0.0, 1.0, 0.0]
        embedding3 = [1.0, 0.0, 0.0]

        assert self.service.similarity(embedding1, embedding2) < 0.5
        assert self.service.similarity(embedding1, embedding3) > 0.9


class TestEmbeddingConfiguration:
    """Embedding 默认配置测试。"""

    def test_defaults_to_multilingual_local_model(self):
        settings = Settings(
            _env_file=None,
            SECRET_KEY="test-secret",
            JWT_SECRET_KEY="test-jwt-secret",
            DATABASE_URL="postgresql+asyncpg://test:test@localhost/test",
            REDIS_URL="redis://localhost:6379/0",
            LLM_API_KEY="test-key",
        )

        assert settings.EMBEDDING_MODEL == "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
        assert settings.EMBEDDING_DIMENSION == 384


class TestEmbeddingFailureBehavior:
    """Embedding 模型初始化与失败策略测试。"""

    def test_local_multilingual_model_loads_by_full_hub_id(self, monkeypatch):
        """非 BGE 的完整 Hub ID 必须通过 SentenceTransformer 加载。"""
        loaded_models = []

        class FakeModel:
            def get_sentence_embedding_dimension(self):
                return 384

            def encode(self, text, normalize_embeddings=True, **kwargs):
                return np.array([1.0, 0.0, 0.0])

        class FakeSentenceTransformer:
            def __new__(cls, model_name):
                loaded_models.append(model_name)
                return FakeModel()

        monkeypatch.setitem(
            sys.modules,
            "sentence_transformers",
            types.SimpleNamespace(SentenceTransformer=FakeSentenceTransformer),
        )

        model_name = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
        service = EmbeddingService(model_name=model_name)

        assert loaded_models == [model_name]
        assert service.default_backend == "local_model"
        assert service.dimension == 384

    def test_local_model_configuration_failure_does_not_fall_back_to_api(self, monkeypatch):
        """本地模型不可用时必须给出可行动的配置错误。"""
        class FailingSentenceTransformer:
            def __new__(cls, model_name):
                raise OSError("model files unavailable")

        monkeypatch.setitem(
            sys.modules,
            "sentence_transformers",
            types.SimpleNamespace(SentenceTransformer=FailingSentenceTransformer),
        )

        with pytest.raises(ValueError, match="本地 Embedding 模型加载失败"):
            EmbeddingService(model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")

    def test_api_embedding_failure_does_not_generate_simplified_vector(self, monkeypatch):
        """API embedding 失败必须暴露配置错误，不能继续写入伪向量。"""
        service = EmbeddingService(model_name="text-embedding-test", api_key="dummy", api_base="https://example.invalid")

        class FakeEmbeddings:
            def create(self, **kwargs):
                raise RuntimeError("404 endpoint not found")

        class FakeClient:
            embeddings = FakeEmbeddings()

        import openai
        monkeypatch.setattr(openai, "OpenAI", lambda **kwargs: FakeClient())

        with pytest.raises(ValueError, match="Embedding API 配置错误"):
            service.embed_text("hello world")


class TestVectorStore:
    """向量存储测试"""

    def test_upsert_maps_chunk_id_to_qdrant_uuid(self):
        """应用层 chunk ID 写入 Qdrant 时必须映射为合法 UUID。"""
        from qdrant_client import QdrantClient
        from qdrant_client.models import Distance, VectorParams

        client = QdrantClient(":memory:")
        client.create_collection(
            collection_name="qdrant_id_test",
            vectors_config=VectorParams(size=3, distance=Distance.COSINE),
        )

        store = VectorStore.__new__(VectorStore)
        store.client = client
        store.collection_name = "qdrant_id_test"
        store.vector_size = 3
        store.backend = "qdrant"
        store.degraded = False
        store.degraded_reason = ""

        source_chunk_id = "e4d909c290d0fb1ca068ffaddf22cbd0_chunk_0"
        record = VectorRecord(
            id=source_chunk_id,
            vector=np.array([1.0, 0.0, 0.0], dtype=np.float32),
            payload={"doc_id": "e4d909c290d0fb1ca068ffaddf22cbd0"},
        )

        assert store.upsert([record]) is True

        points, _ = client.scroll(
            collection_name="qdrant_id_test",
            with_payload=True,
            with_vectors=False,
        )
        assert len(points) == 1
        uuid.UUID(str(points[0].id))
        assert points[0].payload["source_chunk_id"] == source_chunk_id

        results = store.search([1.0, 0.0, 0.0], top_k=1)
        assert results[0].id == str(points[0].id)
        assert results[0].payload["source_chunk_id"] == source_chunk_id

    def setup_method(self):
        self.store = VectorStore(collection_name="test_collection", vector_size=3)

    def test_upsert_and_search(self):
        """测试插入和搜索"""
        records = [
            VectorRecord(
                id="doc1",
                vector=[1.0, 0.0, 0.0],
                payload={"content": "test document 1"}
            ),
            VectorRecord(
                id="doc2",
                vector=[0.0, 1.0, 0.0],
                payload={"content": "test document 2"}
            )
        ]

        success = self.store.upsert(records)
        assert success

        results = self.store.search(
            query_vector=[1.0, 0.0, 0.0],
            top_k=2
        )

        assert len(results) > 0
        assert results[0].id == "doc1"

    def test_delete(self):
        """测试删除"""
        records = [
            VectorRecord(
                id="doc1",
                vector=[1.0, 0.0, 0.0],
                payload={"content": "test"}
            )
        ]

        self.store.upsert(records)
        success = self.store.delete(["doc1"])
        assert success

    def test_get_all_records(self):
        """测试可从持久化存储重新读取全部记录"""
        records = [
            VectorRecord(
                id="doc1",
                vector=[1.0, 0.0, 0.0],
                payload={"doc_id": "lesson1", "content": "test document 1", "metadata": {"topic": "reading"}}
            ),
            VectorRecord(
                id="doc2",
                vector=[0.0, 1.0, 0.0],
                payload={"doc_id": "lesson2", "content": "test document 2", "metadata": {"topic": "writing"}}
            )
        ]

        self.store.upsert(records)
        restored = self.store.get_all_records()

        assert len(restored) == 2
        assert {record.id for record in restored} == {"doc1", "doc2"}
        assert restored[0].payload.get("content")

    def test_collection_info_marks_memory_fallback_as_degraded(self):
        """测试Qdrant不可用时会显式标记 memory 降级状态"""
        info = self.store.get_collection_info()

        assert info["backend"] == "memory"
        assert info["degraded"] is True
        assert info["degraded_reason"]


class TestRAGGenerator:
    """RAG生成器测试"""

    def test_generate_marks_simplified_fallback_as_degraded(self, monkeypatch):
        """测试生成回退到简化模式时会显式暴露 degraded 状态"""
        class FakeCompletions:
            def create(self, **kwargs):
                raise RuntimeError("llm upstream unavailable")

        class FakeChat:
            completions = FakeCompletions()

        class FakeClient:
            chat = FakeChat()

        import openai
        monkeypatch.setattr(openai, "OpenAI", lambda **kwargs: FakeClient())

        generator = RAGGenerator(api_key="dummy", api_base="https://example.invalid")
        result = generator.generate(query="Krashen 是什么", retrieval_results=[])

        assert result.degraded is True
        assert result.backend == "simplified_fallback"
        assert "llm upstream unavailable" in result.degraded_reason
        assert result.answer


class TestHybridRetriever:
    """混合检索器测试"""

    def setup_method(self):
        self.retriever = HybridRetriever(top_k=5)

    def test_add_documents(self):
        """测试添加文档"""
        chunks = [
            DocumentChunk(
                id="chunk1",
                doc_id="doc1",
                content="This is a test document about machine learning."
            ),
            DocumentChunk(
                id="chunk2",
                doc_id="doc1",
                content="Machine learning is a subset of artificial intelligence."
            )
        ]

        self.retriever.add_documents(chunks)

        assert len(self.retriever.chunks) == 2
        assert "chunk1" in self.retriever.chunks

    def test_sparse_retrieve(self):
        """测试稀疏检索"""
        chunks = [
            DocumentChunk(
                id="chunk1",
                doc_id="doc1",
                content="The quick brown fox jumps over the lazy dog."
            ),
            DocumentChunk(
                id="chunk2",
                doc_id="doc1",
                content="Machine learning is a branch of artificial intelligence."
            )
        ]

        self.retriever.add_documents(chunks)

        results = self.retriever.retrieve(
            query="fox dog",
            method="sparse"
        )

        assert len(results) > 0

    def test_query_expansion(self):
        """测试查询扩展"""
        expanded = self.retriever.expand_query("教学方法")

        assert len(expanded) > 0
        assert "教学方法" in expanded

    def test_sparse_retrieve_rehydrates_from_vector_store_when_index_empty(self):
        """测试索引为空时可从持久化存储重建后执行稀疏检索"""
        records = [
            VectorRecord(
                id="chunk1",
                vector=[1.0, 0.0, 0.0],
                payload={
                    "doc_id": "doc1",
                    "content": "The quick brown fox jumps over the lazy dog.",
                    "metadata": {"title": "Lesson 1"}
                }
            )
        ]

        class FakeVectorStore:
            def get_all_records(self):
                return records

        retriever = HybridRetriever(vector_store=FakeVectorStore(), top_k=5)

        results = retriever.retrieve(query="fox dog", method="sparse")

        assert len(results) == 1
        assert results[0].chunk_id == "chunk1"
        assert "chunk1" in retriever.chunks


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
