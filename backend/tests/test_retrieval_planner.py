from types import SimpleNamespace

from app.services.analysis.dual_retriever import DualRetriever


def test_dual_retriever_uses_structured_retrieval_plan(monkeypatch):
    class FakePlanner:
        def build(self, wiki_tags, rag_tags, enhancement_tags, text_title):
            return SimpleNamespace(
                wiki_query="planner wiki query",
                rag_query="planner rag query",
                strategy="support_first",
                risk_flags=["i_plus_2_risk"],
                primary_focus=["support"],
            )

    monkeypatch.setattr("app.services.analysis.dual_retriever.RetrievalPlanner", FakePlanner, raising=False)

    captured = {}

    def fake_search_wiki(self, query, max_results):
        captured["wiki_query"] = query
        return []

    def fake_search_rag(self, query, max_results):
        captured["rag_query"] = query
        return []

    monkeypatch.setattr(DualRetriever, "_search_wiki", fake_search_wiki)
    monkeypatch.setattr(DualRetriever, "_search_rag", fake_search_rag)

    retriever = DualRetriever()
    result = retriever.retrieve(
        wiki_tags=["i_plus_2_risk"],
        rag_tags=["i_plus_2_risk"],
        enhancement_tags=["very_long_sentences"],
        text_title="Academic Reading",
    )

    assert result.wiki_query_used == "planner wiki query"
    assert result.rag_query_used == "planner rag query"
    assert captured["wiki_query"] == "planner wiki query"
    assert captured["rag_query"] == "planner rag query"


def test_retrieval_plan_prioritizes_support_for_i_plus_2_risk():
    from app.services.analysis.retrieval_planner import RetrievalPlanner

    planner = RetrievalPlanner()
    plan = planner.build(
        wiki_tags=["i_plus_2_risk", "very_long_sentences"],
        rag_tags=["i_plus_2_risk", "very_long_sentences"],
        enhancement_tags=["i_plus_2_risk", "very_long_sentences"],
        text_title="Academic Reading",
    )

    assert plan.strategy == "support_first"
    assert "i_plus_2_risk" in plan.risk_flags
    assert "Krashen" in plan.wiki_query or "支架" in plan.wiki_query
    assert "支架" in plan.rag_query or "双语词汇表" in plan.rag_query
