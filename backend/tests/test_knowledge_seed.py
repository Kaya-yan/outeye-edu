"""
系统知识种子测试（TDD）

目标：
1. 系统种子文档为 system 作用域，全员可见
2. 种子内容匿名化（不含邮箱/人名等个人标识）
"""

import re

import pytest

from app.core.scope import SCOPE_SYSTEM
from app.services.knowledge_seed import SYSTEM_SEED_DOCUMENTS, seed_system_knowledge


class TestSystemSeedDocuments:
    """系统种子文档测试"""

    def test_seed_documents_are_present(self):
        """应存在系统种子文档"""
        assert len(SYSTEM_SEED_DOCUMENTS) > 0

    def test_seed_documents_are_anonymized(self):
        """种子内容不应包含邮箱、手机号等个人标识"""
        email_pattern = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
        phone_pattern = re.compile(r"1[3-9]\d{9}")

        for doc in SYSTEM_SEED_DOCUMENTS:
            combined = doc["title"] + doc["content"]
            assert not email_pattern.search(combined), f"种子包含邮箱: {doc['title']}"
            assert not phone_pattern.search(combined), f"种子包含手机号: {doc['title']}"

    def test_seed_documents_have_scope_system(self):
        """每个种子文档应标记为 system 作用域"""
        for doc in SYSTEM_SEED_DOCUMENTS:
            assert doc.get("scope") == SCOPE_SYSTEM


class TestSeedSystemKnowledge:
    """系统知识播种逻辑测试"""

    def test_seed_builds_system_scope_payload(self, monkeypatch):
        """播种应使用 system 作用域写入（不绑定具体用户）"""
        captured = []

        class FakeEmbedding:
            def embed_text(self, text):
                return type("R", (), {"embedding": [0.1, 0.2, 0.3]})()

        class FakeVectorStore:
            def __init__(self):
                self.upserted = []
            def upsert(self, records):
                self.upserted.extend(records)
                return True
            def get_all_records(self):
                return []

        store = FakeVectorStore()

        docs = [
            {"title": "测试理论", "content": "匿名化教学内容", "scope": SCOPE_SYSTEM}
        ]
        monkeypatch.setattr(
            "app.services.knowledge_seed.SYSTEM_SEED_DOCUMENTS", docs
        )

        result = seed_system_knowledge(store, FakeEmbedding())

        assert result["seeded"] == 1
        for record in store.upserted:
            assert record.payload.get("scope") == SCOPE_SYSTEM
