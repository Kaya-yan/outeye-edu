"""④a 三层架构 HTML 课件生成测试：内容层解析/程序自检/逐页重生成/拼装/回退"""

import pytest

from app.services.courseware_llm_generator import (
    ACCENT_PALETTE,
    DEFAULT_ACCENT,
    THEME_TOKENS,
    _assemble_skeleton,
    _ContentPage,
    _parse_pages,
    _sanitize_page,
    _validate_content_page,
    _validate_deck,
    contrast_ratio,
    generate_html_courseware,
)


def _page(title: str, body: str, intent: str = "教学意图示例文本") -> str:
    return (
        f"```html\n<!--page: 1 | {title}-->\n<!--intent: {intent}-->\n{body}\n```\n"
    )


GOOD_BODY = (
    '<div class="kicker">STAGE 1 · READING · 15 MIN</div>'
    "<h2>Deep Reading</h2>"
    '<div class="page-focus"><p>We start with the longest sentence and see how it works.</p></div>'
    '<p class="quote-src">from paragraph 1</p>'
)


def _deck_answer(n_pages: int = 5, accent: str = "#35507a", *, page_bodies=None) -> str:
    interactions = [
        '<details class="reveal"><summary>Q1</summary><p>A1</p></details>',
        '<div class="vocab-grid"><div class="vocab-card"><div class="inner"><div class="front">word</div><div class="back">释义（第1段）</div></div></div></div>',
        '<ol class="timeline"><li>step one</li><li>step two</li></ol>',
    ]
    bodies = page_bodies or []
    parts = [f"ACCENT: {accent}\n"]
    for i in range(n_pages):
        body = bodies[i] if i < len(bodies) else GOOD_BODY + interactions[i % len(interactions)]
        title = f"Page {i + 1}"
        parts.append(f"```html\n<!--page: {i + 1} | {title}-->\n<!--intent: 意图{i + 1}-->\n{body}\n```\n")
    parts.append('```json\n{"prompt_version": "v2", "pages_count": %d}\n```\n' % n_pages)
    return "\n".join(parts)


class _FakeRAG:
    use_api = True
    replies: list = []

    def __init__(self, **kwargs):
        pass

    def _generate_with_api(self, messages):
        reply = type(self).replies.pop(0) if type(self).replies else _deck_answer()
        return reply, {}


@pytest.fixture()
def fake_llm(monkeypatch):
    def install(*replies: str):
        _FakeRAG.replies = list(replies)
        monkeypatch.setattr("app.services.rag.RAGGenerator", _FakeRAG)

    return install


def _plan(n_activities: int = 4) -> dict:
    return {
        "activity_designs": [
            {"name": f"环节{i}", "duration": "10 分钟", "objective": "obj", "steps": "steps"}
            for i in range(1, n_activities + 1)
        ],
        "objectives": [{"text": "read"}],
    }


def _run(monkeypatch_install=None):
    return generate_html_courseware(
        title="测试课件",
        plan=_plan(),
        analysis={},
        text="A" * 200,
    )


# ---- 主题与对比度 ----


def test_theme_token_contrast_meets_wcag_aa():
    paper = THEME_TOKENS["paper"]
    for name, hexc in THEME_TOKENS.items():
        if name == "paper":
            continue
        assert contrast_ratio(hexc, paper) >= 4.5, f"{name} 低于 4.5:1"
    for hexc in ACCENT_PALETTE:
        assert contrast_ratio(hexc, paper) >= 4.5, f"{hexc} 低于 4.5:1"


def test_skeleton_assembly_replaces_all_markers():
    pages = [_ContentPage(title="封面", intent="建立情境", html=GOOD_BODY)]
    html = _assemble_skeleton("Test <Title> & Deck", "#b5493e", pages)
    assert "__TITLE__" not in html and "__ACCENT__" not in html and "__ACCENT_SOFT__" not in html
    assert "<!--SECTIONS-->" not in html
    assert html.count('<section class="page"') == 1
    assert 'data-page="1"' in html and 'data-intent="建立情境"' in html
    assert "--accent:#b5493e" in html
    assert "Test &lt;Title&gt; &amp; Deck" in html
    # 框架层要素写死在骨架，拼装后必须存在
    for marker in ('id="nav-prev"', 'id="nav-next"', 'id="page-indicator"', "--fs-body:21px", "--lh-body:1.8"):
        assert marker in html, marker


# ---- 解析与自检 ----


def test_parse_pages_inside_fence_contract():
    accent, pages = _parse_pages(_deck_answer(3))
    assert accent == "#35507a"
    assert len(pages) == 3
    assert pages[0].title == "Page 1" and pages[2].intent == "意图3"
    assert all("<!--" not in p.html for p in pages)


def test_parse_pages_lookback_when_comments_outside_fence():
    answer = (
        "ACCENT: #b5493e\n\n"
        "<!--page: 7 | 检测-->\n"
        "<!--intent: 检验理解-->\n"
        f"```html\n{GOOD_BODY}\n```\n"
    )
    accent, pages = _parse_pages(answer)
    assert accent == "#b5493e"
    assert pages[0].title == "检测" and pages[0].intent == "检验理解"


def test_validate_content_page_catches_violations():
    bad = _ContentPage(
        title="x",
        intent="",
        html=(
            '<div class="page-focus"><p style="color:#ff0000">a</p></div>'
            '<div class="page-focus"></div>'
            "<script>alert(1)</script>"
        ),
    )
    probs = _validate_content_page(bad)
    joined = "；".join(probs)
    for keyword in ("page-focus", "禁用标签", "色值"):
        assert keyword in joined, probs


def test_validate_content_page_allows_layout_inline_style():
    ok = _ContentPage(title="x", intent="", html=GOOD_BODY.replace("<p>", '<p style="margin-top:24px;text-align:center">', 1))
    assert _validate_content_page(ok) == []


def test_validate_deck_requires_pages_and_interactions():
    single = [_ContentPage("t", "i", GOOD_BODY)]
    reason = _validate_deck(single, min_pages=3)
    assert reason and "页面数不足" in reason
    pages = [_ContentPage("t", "i", GOOD_BODY) for _ in range(4)]
    reason = _validate_deck(pages, min_pages=3)
    assert reason and "交互类型不足" in reason


def test_sanitize_page_strips_hard_violations():
    dirty = '<div class="page-focus"><p style="color:#ff0000;background:#eee">a</p><span onclick="x()">go</span></div><iframe src="http://evil"></iframe>'
    clean = _sanitize_page(dirty)
    assert "<iframe" not in clean and "#ff0000" not in clean and "onclick" not in clean and "background" not in clean


# ---- 端到端（fake LLM）----


def test_happy_path_assembles_skeleton(fake_llm):
    fake_llm(_deck_answer(6))
    result = _run()
    assert result.fallback is False
    assert result.prompt_version == "v2"
    assert result.html.startswith("<!DOCTYPE html>")
    assert result.html.count('<section class="page"') == 6
    assert result.self_check["pages_count"] == 6
    assert result.self_check["accent"] == "#35507a"
    assert result.self_check["regenerated_pages"] == []
    assert result.self_check["llm_self_check"].get("pages_count") == 6


def test_invalid_accent_falls_back_to_default(fake_llm):
    fake_llm(_deck_answer(5, accent="#ff00ff"))
    result = _run()
    assert result.fallback is False
    assert result.self_check["accent"] == DEFAULT_ACCENT
    assert result.self_check["accent_note"]


def test_bad_page_regenerated(fake_llm):
    bad_body = (
        '<div class="page-focus"><p style="color:#ff0000">raw color here</p></div>'
        '<div class="page-focus"></div>'
    )
    bodies = [
        GOOD_BODY + '<ol class="timeline"><li>step one</li><li>step two</li></ol>',
        bad_body,
        GOOD_BODY + '<details class="reveal"><summary>Q</summary><p>A</p></details>',
        GOOD_BODY + '<div class="vocab-card"><div class="inner"><div class="front">w</div><div class="back">释义</div></div></div>',
        GOOD_BODY,
    ]
    first = _deck_answer(5, page_bodies=bodies)
    # 第一次：整副应答；第二次：单页重生成返回合规页
    fixed_page = (
        "```html\n<!--page: 2 | Page 2-->\n<!--intent: 意图2-->\n"
        '<div class="page-focus"><p>fixed page content that is comfortably long enough to pass '
        "the minimum length validation rule for a single content page in this deck.</p>"
        '<p class="quote-src">from paragraph 2</p></div>\n```\n'
    )
    fake_llm(first, fixed_page)
    result = _run()
    assert result.fallback is False
    assert result.self_check["regenerated_pages"] == [2]
    assert 'style="color:#ff0000"' not in result.html


def test_deck_failure_retries_then_falls_back(fake_llm):
    too_few = _deck_answer(2)
    fake_llm(too_few, too_few)
    result = _run()
    assert result.fallback is True
    assert result.retries == 1
    assert result.self_check.get("prompt_version") == "fallback"
    assert result.model == "template-fallback"


def test_regen_failure_sanitizes(fake_llm):
    bad_body = '<div class="page-focus"><p style="color:#ff0000">raw color</p></div>'
    bodies = [
        GOOD_BODY + '<ol class="timeline"><li>step one</li><li>step two</li></ol>',
        bad_body,
        GOOD_BODY + '<details class="reveal"><summary>Q</summary><p>A</p></details>',
        GOOD_BODY + '<div class="vocab-card"><div class="inner"><div class="front">w</div><div class="back">释义</div></div></div>',
        GOOD_BODY,
    ]
    first = _deck_answer(5, page_bodies=bodies)
    # 重生成两轮都失败（返回同样违规的页）→ 轮次用尽后走确定性净化
    bad_regen = (
        "```html\n<!--page: 2 | Page 2-->\n<!--intent: 意图2-->\n" + bad_body + "\n```\n"
    )
    fake_llm(first, bad_regen, bad_regen)
    result = _run()
    assert result.fallback is False
    assert result.self_check["sanitized_pages"] == [2]
    assert "#ff0000" not in result.html
