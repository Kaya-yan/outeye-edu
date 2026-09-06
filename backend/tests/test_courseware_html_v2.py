"""④a 三层架构 HTML 课件单元测试：内容层解析/程序自检/净化/拼装/对比度
（③ 起整副生成改为两阶段：规划器+逐页，端到端用例见 test_courseware_two_stage.py）"""

from app.services.courseware_llm_generator import (
    ACCENT_PALETTE,
    THEME_TOKENS,
    _assemble_skeleton,
    _ContentPage,
    _parse_pages,
    _sanitize_page,
    _validate_content_page,
    contrast_ratio,
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


def test_skeleton_carries_close_reading_components():
    """③ 骨架必须内置逐段精讲组件样式与解剖交互脚本（含放映隐藏教学意图）"""
    pages = [_ContentPage(title="p", intent="i", html='<div class="page-focus"><p class="anatomy-sentence"><span class="cl cl-core">x</span></p></div>')]
    html = _assemble_skeleton("T", "#35507a", pages)
    for marker in (".para-original", "mark.kw", ".para-gist", ".sentence-anatomy", ".anatomy-sentence .cl", ".anatomy-legend", ".anatomy-tip", ".sent-walk", ".lang-points", ".cohesion-note", ".teaching-intent"):
        assert marker in html, marker
    assert "anatomy-sentence .cl" in html and "classList.toggle('lit')" in html
    assert "x-ray" in html
    assert "body.oe-edit-all .teaching-intent{display:block" in html


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


def test_validate_content_page_accepts_close_reading_components():
    body = (
        '<div class="kicker">课文精讲</div><h2>T</h2><div class="page-focus">'
        '<blockquote class="para-original"><p>Text with <mark class="kw">word</mark>.</p><footer>—— Para. 1</footer></blockquote>'
        '<div class="para-gist"><h3>主旨</h3><p>概括。</p></div>'
        '<div class="sentence-anatomy"><p class="anatomy-sentence"><span class="cl cl-core">Core</span> <span class="cl cl-mod">mod</span>.</p>'
        '<ul class="anatomy-legend"><li>说明</li></ul><p class="anatomy-tip">翻译。</p></div>'
        '<div class="sent-walk"><details><summary>句 1</summary><p>讲解。</p></details></div>'
        '<div class="lang-points"><ol><li>point</li></ol></div>'
        '<div class="cohesion-note"><h3>衔接</h3><p>功能。</p></div>'
        '<aside class="teaching-intent">意图。</aside>'
        "</div>"
    )
    assert _validate_content_page(_ContentPage(title="x", intent="i", html=body)) == []


def test_sanitize_page_strips_hard_violations():
    dirty = '<div class="page-focus"><p style="color:#ff0000;background:#eee">a</p><span onclick="x()">go</span></div><iframe src="http://evil"></iframe>'
    clean = _sanitize_page(dirty)
    assert "<iframe" not in clean and "#ff0000" not in clean and "onclick" not in clean and "background" not in clean
