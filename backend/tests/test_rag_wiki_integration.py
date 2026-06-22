from types import SimpleNamespace

from app.api.api_v1.endpoints.rag import _do_wiki_query
from app.services.rag.generator import RAGGenerator


class FakeRetriever:
    def retrieve(self, query, method, top_k, filter_conditions):
        return []

    def rerank(self, query, results, top_k):
        return results


class FakeGenerator:
    def __init__(self):
        self.captured_wiki_results = None

    def generate_with_wiki(self, query, wiki_results, rag_results):
        self.captured_wiki_results = wiki_results
        return SimpleNamespace(
            answer="ok",
            sources=[],
            confidence=0.9,
            response_time=0.01,
            model="test-model",
        )


def test_do_wiki_query_uses_query_constructor_and_normalizes_wiki_results(monkeypatch):
    fake_generator = FakeGenerator()

    monkeypatch.setattr(
        "app.api.api_v1.endpoints.rag.get_rag_services",
        lambda: {"retriever": FakeRetriever(), "generator": fake_generator},
    )

    class FakeWikiQuery:
        def __init__(self, wiki_root):
            self.wiki_root = wiki_root

        def query(self, query_text, max_results=10):
            frontmatter = SimpleNamespace(
                title="Wiki Title",
                confidence="high",
                contested=False,
                contradictions=["legacy-page"],
                sources=["raw/a.md"],
                updated="2026-06-17",
                tags=["reading"],
            )
            page = SimpleNamespace(filename="wiki-title", frontmatter=frontmatter, content="Wiki content")
            return [SimpleNamespace(page=page, relevance_score=0.95, match_type="content", matched_sections=["Overview"])]

    monkeypatch.setattr("app.services.wiki.WikiQuery", FakeWikiQuery)
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///tmp/test.db")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("LLM_API_KEY", "dummy")
    monkeypatch.setenv("JWT_SECRET_KEY", "test-jwt-secret")
    monkeypatch.setenv("WIKI_DATA_PATH", "C:/wiki-root")

    data = _do_wiki_query("krashen", "hybrid", 3, None, True)

    assert data["answer"] == "ok"
    assert fake_generator.captured_wiki_results == [
        {
            "title": "Wiki Title",
            "content": "Wiki content",
            "relevance_score": 0.95,
            "match_type": "content",
            "matched_sections": ["Overview"],
            "tags": ["reading"],
            "confidence": "high",
            "contested": False,
            "contradictions": ["legacy-page"],
            "sources": ["raw/a.md"],
            "updated": "2026-06-17",
        }
    ]


def test_generate_with_wiki_includes_frontmatter_signals_in_prompt(monkeypatch):
    generator = RAGGenerator(api_key="dummy", api_base="https://example.invalid")
    captured = {}

    def fake_generate(messages):
        captured["messages"] = messages
        return "ok", {}

    monkeypatch.setattr(generator, "_generate_with_api", fake_generate)
    generator.use_api = True

    generator.generate_with_wiki(
        query="什么是支架教学",
        wiki_results=[
            {
                "title": "Curated Reading Guide",
                "content": "Wiki content",
                "confidence": "high",
                "contested": True,
                "contradictions": ["legacy-reading-note"],
                "sources": ["raw/a.md", "raw/b.md"],
                "updated": "2026-06-17",
            }
        ],
        rag_results=[],
    )

    user_prompt = captured["messages"][-1]["content"]
    assert "置信度" in user_prompt
    assert "存在争议" in user_prompt
    assert "legacy-reading-note" in user_prompt
    assert "来源" in user_prompt
    assert "2026-06-17" in user_prompt
