"""任务F2 难词解析卡测试：课文原句提取 / 详情解析 / 缓存三路径 / word-details 端点 / 词汇讲义导出"""

import json
from urllib.parse import quote

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.core.security import get_current_user
from app.models.analysis import WordDetailCache
from app.services.analysis.word_detail import (
    extract_original_sentence,
    _extract_details,
    fetch_word_details,
)
from app.services.analysis.export_service import export_vocab_handout

TEXT = (
    "Blue jeans are favored equally by bureaucrats and cowboys. "
    "However, their origins are humble: they were stitched by a peddler named Levi Strauss. "
    "Copper rivets made the pockets strong."
)


class TestExtractOriginalSentence:
    def test_exact_word_match(self):
        s = extract_original_sentence(TEXT, "bureaucrats")
        assert s == "Blue jeans are favored equally by bureaucrats and cowboys."

    def test_word_form_variant_via_stem(self):
        # 课文里是复数 rivets，查询用原形 rivet，词干前缀容错应命中
        s = extract_original_sentence(TEXT, "rivet")
        assert s == "Copper rivets made the pockets strong."

    def test_case_insensitive(self):
        assert "bureaucrats" in extract_original_sentence(TEXT, "BUREAUCRATS")

    def test_no_match_returns_empty(self):
        assert extract_original_sentence(TEXT, "elephant") == ""

    def test_empty_inputs(self):
        assert extract_original_sentence("", "rivet") == ""
        assert extract_original_sentence(TEXT, "") == ""


class TestExtractDetails:
    def test_fenced_json_block(self):
        answer = '前置说明\n```json\n{"words": [{"word": "rivet", "phonetic": "/ˈrɪvɪt/", "gloss": "铆钉"}]}\n```'
        assert _extract_details(answer)[0]["word"] == "rivet"

    def test_bare_json(self):
        answer = '{"words": [{"word": "Rivet", "gloss": "铆钉"}]}'
        got = _extract_details(answer)
        assert len(got) == 1 and got[0]["word"] == "rivet"  # 词形归一小写

    def test_invalid_returns_empty(self):
        assert _extract_details("完全不是 JSON") == []
        assert _extract_details('{"words": "不是列表"}') == []

    def test_filters_entries_without_any_detail_field(self):
        answer = json.dumps({"words": [
            {"word": "rivet", "gloss": "铆钉"},
            {"word": "empty"},
        ]})
        got = _extract_details(answer)
        assert [w["word"] for w in got] == ["rivet"]


def _session_factory(test_engine):
    return sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)


class TestFetchWordDetails:
    @pytest.mark.asyncio
    async def test_cache_hit_skips_llm(self, test_engine, monkeypatch):
        monkeypatch.setattr("app.core.database.AsyncSessionLocal", _session_factory(test_engine))
        payload = {"phonetic": "/ˈbjʊərəkræt/", "pos": "n.", "gloss": "官僚",
                   "teaching_example": "The bureaucrats approved the plan.", "board_note": "bureaucrat n. 官僚"}
        factory = _session_factory(test_engine)
        async with factory() as db:
            db.add(WordDetailCache(word="bureaucrat", lang="en", payload_json=json.dumps(payload)))
            await db.commit()

        def _boom(*a, **k):
            raise AssertionError("缓存命中时不应调用 LLM")

        monkeypatch.setattr("app.services.analysis.word_detail._llm_details", _boom)

        details, meta = await fetch_word_details(["bureaucrat"], TEXT)
        assert meta == {"cache_hits": 1, "llm_generated": 0, "fallback": False}
        d = details["bureaucrat"]
        assert d["source"] == "cached"
        assert d["phonetic"] == "/ˈbjʊərəkræt/"
        # 课文原句确定性提取：课文里是复数，词干容错命中
        assert "bureaucrats" in d["original_sentence"]

    @pytest.mark.asyncio
    async def test_llm_generated_and_cached(self, test_engine, monkeypatch):
        monkeypatch.setattr("app.core.database.AsyncSessionLocal", _session_factory(test_engine))
        fake = [{
            "word": "rivet", "phonetic": "/ˈrɪvɪt/", "pos": "n.", "gloss": "铆钉",
            "teaching_example": "Copper rivets hold the pockets together.",
            "board_note": "rivet /ˈrɪvɪt/ n. 铆钉\n→ Copper rivets hold the pockets together.",
        }]
        monkeypatch.setattr("app.services.analysis.word_detail._llm_details", lambda words, ctx: fake)

        details, meta = await fetch_word_details(["rivet"], TEXT)
        assert meta == {"cache_hits": 0, "llm_generated": 1, "fallback": False}
        assert details["rivet"]["source"] == "llm"

        # 生成结果落库；同词再取直接命中缓存，零 LLM
        factory = _session_factory(test_engine)
        async with factory() as db:
            rows = (await db.execute(select(WordDetailCache))).scalars().all()
        assert len(rows) == 1 and rows[0].word == "rivet"

        details2, meta2 = await fetch_word_details(["rivet"], TEXT)
        assert meta2["cache_hits"] == 1 and meta2["llm_generated"] == 0
        assert details2["rivet"]["source"] == "cached"

    @pytest.mark.asyncio
    async def test_llm_failure_degrades_to_fallback(self, test_engine, monkeypatch):
        monkeypatch.setattr("app.core.database.AsyncSessionLocal", _session_factory(test_engine))

        def _fail(words, ctx):
            raise RuntimeError("LLM 不可用")

        monkeypatch.setattr("app.services.analysis.word_detail._llm_details", _fail)

        details, meta = await fetch_word_details(["rivet"], TEXT)
        assert meta["fallback"] is True
        d = details["rivet"]
        assert d["source"] == "miss"
        assert d["phonetic"] == "" and d["gloss"] == ""
        # 原句提取不依赖 LLM，失败时仍返回
        assert d["original_sentence"] == "Copper rivets made the pockets strong."

    @pytest.mark.asyncio
    async def test_dedupe_case_insensitive_and_strip(self, test_engine, monkeypatch):
        monkeypatch.setattr("app.core.database.AsyncSessionLocal", _session_factory(test_engine))
        seen = []

        def fake_llm(words, ctx):
            seen.append(words)
            return []

        monkeypatch.setattr("app.services.analysis.word_detail._llm_details", fake_llm)

        details, _ = await fetch_word_details(["Rivet", "rivet", "  "], TEXT)
        assert list(details.keys()) == ["rivet"]
        assert seen == [["rivet"]]

    @pytest.mark.asyncio
    async def test_empty_words_short_circuits(self):
        details, meta = await fetch_word_details(["", "  "], TEXT)
        assert details == {}
        assert meta == {"cache_hits": 0, "llm_generated": 0, "fallback": False}


@pytest.fixture
def auth_client():
    async def override_auth():
        return {"user_id": "user-1", "email": "test@example.com", "is_admin": False}

    app.dependency_overrides[get_current_user] = override_auth
    yield TestClient(app)
    app.dependency_overrides.clear()


class TestWordDetailsEndpoint:
    def test_returns_details_and_meta(self, auth_client, monkeypatch):
        async def fake_fetch(words, text, lang="en"):
            return (
                {"rivet": {"phonetic": "/ˈrɪvɪt/", "pos": "n.", "gloss": "铆钉",
                           "teaching_example": "…", "board_note": "…",
                           "original_sentence": "Copper rivets made the pockets strong.",
                           "source": "llm"}},
                {"cache_hits": 0, "llm_generated": 1, "fallback": False},
            )

        # 端点在函数体内 import，须打源头模块
        monkeypatch.setattr("app.services.analysis.word_detail.fetch_word_details", fake_fetch)

        res = auth_client.post(
            "/api/v1/analysis/word-details",
            json={"words": ["rivet"], "text": TEXT, "language": "en"},
        )
        assert res.status_code == 200
        body = res.json()
        assert body["details"]["rivet"]["gloss"] == "铆钉"
        assert body["meta"]["fallback"] is False

    def test_requires_auth(self):
        res = TestClient(app).post("/api/v1/analysis/word-details", json={"words": ["rivet"]})
        assert res.status_code == 403

    def test_empty_words_rejected(self, auth_client):
        res = auth_client.post("/api/v1/analysis/word-details", json={"words": []})
        assert res.status_code == 422

    def test_invalid_language_rejected(self, auth_client):
        res = auth_client.post(
            "/api/v1/analysis/word-details",
            json={"words": ["rivet"], "language": "e"},
        )
        assert res.status_code == 422


class TestExportVocabHandout:
    PLAN = {
        "language_name": "英语",
        "text_level": "B2",
        "words": [
            {
                "word": "rivet", "level": "C1", "count": 2,
                "phonetic": "/ˈrɪvɪt/", "pos": "n.", "gloss": "铆钉",
                "original_sentence": "Copper rivets made the pockets strong.",
                "teaching_example": "Copper rivets hold the pockets together.",
                "board_note": "rivet /ˈrɪvɪt/ n. 铆钉\n→ Copper rivets hold the pockets together.",
            },
            {"word": "peddler", "level": "B2", "count": 1},  # 详情缺失字段留空跳段
        ],
    }

    def test_docx_bytes(self):
        buf = export_vocab_handout(self.PLAN, "牛仔裤课文 · 词汇讲义")
        data = buf.getvalue()
        assert data[:2] == b"PK"  # docx 即 zip
        assert len(data) > 1000

    def test_export_endpoint_vocab_format(self, auth_client):
        res = auth_client.post(
            "/api/v1/analysis/export",
            json={"format": "vocab", "title": "牛仔裤课文 · 词汇讲义", "plan": self.PLAN},
        )
        assert res.status_code == 200
        assert "wordprocessingml" in res.headers["content-type"]
        assert res.content[:2] == b"PK"
        cd = res.headers["content-disposition"]
        # RFC 5987：中文文件名双写，filename* 为 UTF-8 编码真名
        assert "filename*=UTF-8''" in cd
        assert quote("牛仔裤课文 · 词汇讲义.docx") in cd
