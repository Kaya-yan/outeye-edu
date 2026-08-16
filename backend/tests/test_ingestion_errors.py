"""
入库错误码映射测试（TDD）

目标：processor 在解析/向量化阶段捕获异常，映射为结构化错误码。
"""

import pytest

from app.services.ingestion.errors import (
    IngestionError,
    ERROR_SCANNED_PDF,
    ERROR_TEXT_ENCODING_FAILED,
    ERROR_EMBEDDING_WAITING,
    ERROR_EMBEDDING_FAILED,
    ERROR_MESSAGES,
)


def _patch_services(monkeypatch, parser=None, embedding=None):
    from app.services.ingestion.processor import _ingest_file_sync

    class DefaultParser:
        def parse_file(self, path):
            return type("Doc", (), {"id": "d1", "title": "t", "content": "hello", "chunks": [
                type("C", (), {"id": "c1", "doc_id": "d1", "content": "hello", "metadata": {}})()
            ]})()

    class DefaultEmbedding:
        def embed_text(self, text):
            return type("R", (), {"embedding": [0.1, 0.2]})()

    class Store:
        def upsert(self, records):
            return True

    monkeypatch.setattr(
        "app.api.api_v1.endpoints.rag.get_rag_services",
        lambda: {
            "parser": parser or DefaultParser(),
            "embedding": embedding or DefaultEmbedding(),
            "vector_store": Store(),
            "retriever": None,
            "generator": None,
        },
    )
    return _ingest_file_sync


class TestIngestionErrorMapping:
    def test_error_messages_defined(self):
        """6 个错误码都应有关联文案"""
        assert ERROR_MESSAGES[ERROR_SCANNED_PDF]
        assert ERROR_MESSAGES[ERROR_TEXT_ENCODING_FAILED]
        assert ERROR_MESSAGES[ERROR_EMBEDDING_WAITING]
        assert ERROR_MESSAGES[ERROR_EMBEDDING_FAILED]

    def test_raises_scanned_pdf_for_empty_pdf(self, monkeypatch):
        """PDF 解析后无文本 → SCANNED_PDF"""
        _ingest = _patch_services(monkeypatch, parser=type(
            "P", (), {"parse_file": lambda self, p: type("Doc", (), {"id": "d1", "title": "scan", "chunks": []})()}
        )())

        with pytest.raises(IngestionError) as e:
            _ingest("scan.pdf", b"%PDF-1.4", "doc-1", {"user_id": "u1"})
        assert e.value.error_code == ERROR_SCANNED_PDF

    def test_raises_text_encoding_failed(self, monkeypatch):
        """UnicodeDecodeError → TEXT_ENCODING_FAILED"""
        def parse(self, p):
            raise UnicodeDecodeError("utf-8", b"", 0, 1, "invalid")
        _ingest = _patch_services(monkeypatch, parser=type("P", (), {"parse_file": parse})())

        with pytest.raises(IngestionError) as e:
            _ingest("file.txt", b"bad", "doc-1", {"user_id": "u1"})
        assert e.value.error_code == ERROR_TEXT_ENCODING_FAILED

    def test_raises_embedding_failed(self, monkeypatch):
        """embedding 推理失败 → EMBEDDING_FAILED"""
        def embed(self, t):
            raise ValueError("本地 Embedding 模型推理失败")
        _ingest = _patch_services(monkeypatch, embedding=type("E", (), {"embed_text": embed})())

        with pytest.raises(IngestionError) as e:
            _ingest("file.txt", b"hello", "doc-1", {"user_id": "u1"})
        assert e.value.error_code == ERROR_EMBEDDING_FAILED

    def test_raises_embedding_waiting(self, monkeypatch):
        """embedding 未初始化 → EMBEDDING_WAITING"""
        def embed(self, t):
            raise ValueError("本地 Embedding 服务未初始化")
        _ingest = _patch_services(monkeypatch, embedding=type("E", (), {"embed_text": embed})())

        with pytest.raises(IngestionError) as e:
            _ingest("file.txt", b"hello", "doc-1", {"user_id": "u1"})
        assert e.value.error_code == ERROR_EMBEDDING_WAITING
