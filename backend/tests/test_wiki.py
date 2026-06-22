import textwrap

from app.services.wiki.query import WikiQuery
from app.services.analysis.fusion_generator import build_wiki_context


def test_query_prefers_high_confidence_non_contested_recent_pages(tmp_path):
    (tmp_path / "a-low.md").write_text(textwrap.dedent("""\
    ---
    title: Legacy Reading Note
    created: 2024-01-01
    updated: 2024-01-02
    type: concept
    tags: [reading]
    sources: []
    confidence: low
    contested: true
    contradictions: [other-page]
    ---
    # Overview
    Scaffolding improves reading comprehension in classroom activities.
    """), encoding="utf-8")

    (tmp_path / "z-high.md").write_text(textwrap.dedent("""\
    ---
    title: Curated Reading Guide
    created: 2026-01-01
    updated: 2026-06-15
    type: concept
    tags: [reading]
    sources: [raw/a.md, raw/b.md]
    confidence: high
    contested: false
    contradictions: []
    ---
    # Overview
    Scaffolding improves reading comprehension in classroom activities.
    """), encoding="utf-8")

    query = WikiQuery(str(tmp_path))
    results = query.query("Scaffolding", max_results=10)

    assert len(results) >= 2
    assert results[0].page.filename == "z-high"


def test_build_wiki_context_includes_frontmatter_signals():
    context = build_wiki_context([
        {
            "title": "Curated Reading Guide",
            "summary": "Scaffolding improves reading comprehension.",
            "confidence": "high",
            "contested": True,
            "contradictions": ["legacy-reading-note"],
            "sources": ["raw/a.md", "raw/b.md"],
            "updated": "2026-06-15",
        }
    ])

    assert "置信度：high" in context
    assert "存在争议" in context
    assert "来源：2" in context
    assert "更新时间：2026-06-15" in context
    assert "legacy-reading-note" in context
