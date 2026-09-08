"""任务A2 交互有效性自检测试：标记结构契约 / 交互类型识别 / 多样性补强 / 重生成轮次上限"""

from types import SimpleNamespace

from app.services.courseware_interaction_check import (
    MIN_DISTINCT_TYPES,
    _pick_diversity_target,
    page_interaction_problems,
    page_interaction_types,
    run_interaction_check,
)


# ---- 单页结构契约（骨架钩子缺失即判不合格）----


def test_reveal_requires_summary():
    bad = '<div class="page-focus"><details class="reveal"><p>答案</p></details></div>'
    assert any("summary" in p for p in page_interaction_problems(bad))
    ok = '<div class="page-focus"><details class="reveal"><summary>问题？</summary><p>答案</p></details></div>'
    assert page_interaction_problems(ok) == []


def test_vocab_card_requires_front_and_back():
    bad = (
        '<div class="vocab-grid"><div class="vocab-card"><div class="inner">'
        '<div class="front">word /wɜːd/</div>'
        "</div></div></div>"
    )
    assert any("front" in p for p in page_interaction_problems(bad))
    ok = bad.replace('<div class="front">word /wɜːd/</div>', '<div class="front">word /wɜːd/</div><div class="back">n. 词</div>')
    assert page_interaction_problems(ok) == []


def test_timer_requires_display_button_and_numeric_seconds():
    bad_seconds = '<div class="timer" data-seconds="90s"><span class="timer-display">90</span><button>开始</button></div>'
    assert any("data-seconds" in p for p in page_interaction_problems(bad_seconds))
    missing_parts = '<div class="timer" data-seconds="90"></div>'
    assert any("timer-display" in p for p in page_interaction_problems(missing_parts))
    ok = '<div class="timer" data-seconds="90"><span class="timer-display">90</span><button>开始</button></div>'
    assert page_interaction_problems(ok) == []


def test_anatomy_sentence_requires_cl_hooks():
    bad = '<p class="anatomy-sentence">This is a plain sentence.</p>'
    assert any("cl-core" in p for p in page_interaction_problems(bad))
    ok = '<p class="anatomy-sentence"><span class="cl cl-core">This is</span> <span class="cl cl-mod">a sentence</span>.</p>'
    assert page_interaction_problems(ok) == []


def test_timeline_requires_two_items():
    bad = '<ol class="timeline"><li>1847</li></ol>'
    assert any("timeline" in p for p in page_interaction_problems(bad))
    ok = '<ol class="timeline"><li>1847</li><li>1873</li></ol>'
    assert page_interaction_problems(ok) == []


def test_sent_walk_details_require_summary():
    bad = '<div class="sent-walk"><details><p>讲解文字。</p></details></div>'
    assert any("summary" in p for p in page_interaction_problems(bad))
    ok = '<div class="sent-walk"><details><summary>句 1：原文</summary><p>讲解文字。</p></details></div>'
    assert page_interaction_problems(ok) == []


# ---- 交互类型识别 / 补强页挑选 ----


def test_page_interaction_types_detection():
    html = (
        '<div class="page-focus"><details class="reveal"><summary>q</summary><p>a</p></details>'
        '<div class="timer" data-seconds="60"><span class="timer-display">60</span><button>go</button></div></div>'
    )
    assert page_interaction_types(html) == {"reveal", "timer"}
    assert MIN_DISTINCT_TYPES == 3


def test_pick_diversity_target_prefers_interaction_then_vocab():
    bp = [{"kind": "cover"}, {"kind": "lang_points"}, {"kind": "vocab"}, {"kind": "interaction"}, {"kind": "summary"}]
    assert _pick_diversity_target(bp, 5) == 3
    bp2 = [{"kind": "cover"}, {"kind": "agenda"}, {"kind": "vocab"}, {"kind": "summary"}]
    assert _pick_diversity_target(bp2, 4) == 2
    bp3 = [{"kind": "cover"}, {"kind": "text_anatomy"}, {"kind": "summary"}]
    assert _pick_diversity_target(bp3, 3) == 1


# ---- run_interaction_check：结构重生成 / 轮次上限 / 多样性补强 ----

RICH = (
    '<details class="reveal"><summary>q</summary><p>a</p></details>'
    '<ol class="timeline"><li>1</li><li>2</li></ol>'
    '<div class="timer" data-seconds="60"><span class="timer-display">60</span><button>go</button></div>'
)


def test_structural_problem_page_regenerated_once_and_clean():
    broken = SimpleNamespace(html='<details class="reveal"><p>答案</p></details>')
    fixed = SimpleNamespace(html=RICH)
    calls = []

    def regen(i, pg, problems):
        calls.append((i, problems))
        return fixed

    pages, summary = run_interaction_check([broken], blueprint=[{"kind": "interaction"}], regen_page=regen)
    assert pages[0] is fixed
    assert len(calls) == 1 and calls[0][0] == 0
    assert any("summary" in p for p in calls[0][1])
    assert summary["structural_problem_pages"] == {"1": calls[0][1]}
    assert summary["regenerated"] == {"1": 1}
    assert summary["diversity_ok"] is True  # 重生成后 reveal/timeline/timer 三种齐备


def test_structural_persists_caps_at_two_rounds_then_diversity_attempt():
    broken_html = '<details class="reveal"><p>答案</p></details>'
    calls = []

    def regen(i, pg, problems):
        calls.append(list(problems))
        return SimpleNamespace(html=broken_html)  # 重生成仍坏

    pages, summary = run_interaction_check(
        [SimpleNamespace(html=broken_html)], blueprint=[{"kind": "interaction"}], regen_page=regen
    )
    # 结构 2 轮封顶 + 多样性 1 次补强尝试
    assert len(calls) == 3
    assert any("交互类型" in " ".join(ps) for ps in calls)
    assert summary["regenerated"] == {"1": 3}
    assert summary["diversity_ok"] is False  # 仍不足只记录，不阻塞产出
    assert pages[0].html == broken_html


def test_diversity_rescue_regenerates_target_page_with_hints():
    pages = [
        SimpleNamespace(html="<p>cover</p>"),
        SimpleNamespace(html='<details class="reveal"><summary>q</summary><p>a</p></details>'),
        SimpleNamespace(html='<p class="anatomy-sentence"><span class="cl cl-core">x</span> <span class="cl cl-mod">y</span>.</p>'),
        SimpleNamespace(html="<p>done</p>"),
    ]
    bp = [{"kind": "cover"}, {"kind": "vocab"}, {"kind": "text_anatomy"}, {"kind": "summary"}]
    calls = []

    def regen(i, pg, problems):
        calls.append((i, " ".join(problems)))
        return SimpleNamespace(html=pg.html + '<ol class="timeline"><li>1</li><li>2</li></ol>')

    out, summary = run_interaction_check(pages, blueprint=bp, regen_page=regen)
    assert len(calls) == 1 and calls[0][0] == 1  # 补强 vocab 页（索引 1）
    assert "仅 2 种" in calls[0][1] and "timeline" in calls[0][1]  # 带缺失类型用法提示（timeline 是缺失类型之一）
    assert summary["diversity_ok"] is True
    assert summary["types_found"] == ["anatomy", "reveal", "timeline"]
    assert out[1].html.endswith("</ol>")


def test_clean_diverse_deck_never_regenerates():
    pages = [
        SimpleNamespace(html='<ol class="timeline"><li>1</li><li>2</li></ol>'),
        SimpleNamespace(html='<details class="reveal"><summary>q</summary><p>a</p></details>'),
        SimpleNamespace(html='<div class="timer" data-seconds="60"><span class="timer-display">60</span><button>go</button></div>'),
    ]
    called = []

    def regen(i, pg, problems):
        called.append(i)
        return None

    out, summary = run_interaction_check(
        pages, blueprint=[{"kind": "text_anatomy"}] * 3, regen_page=regen, progress_cb=lambda m: None
    )
    assert called == []
    assert summary["structural_problem_pages"] == {} and summary["regenerated"] == {}
    assert summary["diversity_ok"] is True and len(summary["types_found"]) == 3
    assert out == pages


# ---- 任务B 练习型组件：mark-words / fill-blanks / sort-paragraphs ----

MW_OK = (
    '<div class="mark-words" data-answer="2,4">'
    '<p class="mw-text">Click the past-tense verbs: The news <span class="mw-w">spread</span> quickly, '
    'everyone <span class="mw-w">knows</span> it, and the symbol <span class="mw-w">grew</span> '
    'with each <span class="mw-w">year</span>.</p>'
    '<div class="ix-actions"><button type="button" class="mw-check">检查</button></div>'
    "</div>"
)
FB_OK = (
    '<div class="fill-blanks">'
    '<p class="fb-text">The symbol has now <span class="fb-blank" data-answers="spread"></span> '
    "throughout most of the world.</p>"
    '<div class="ix-actions"><button type="button" class="fb-check">检查</button></div>'
    "</div>"
)
SP_OK = (
    '<div class="sort-paragraphs"><ol class="sp-list">'
    '<li class="sp-item" data-order="2">Levi Strauss arrived in San Francisco.</li>'
    '<li class="sp-item" data-order="1">The gold rush drew people west.</li>'
    '<li class="sp-item" data-order="3">Miners asked for sturdy trousers.</li>'
    '</ol><div class="ix-actions"><button type="button" class="sp-check">检查</button></div></div>'
)


def test_mark_words_contract():
    assert page_interaction_problems(MW_OK) == []
    no_answer = MW_OK.replace(' data-answer="2,4"', "")
    assert any("data-answer" in p for p in page_interaction_problems(no_answer))
    bad_idx = MW_OK.replace('data-answer="2,4"', 'data-answer="2,9"')
    assert any("序号" in p for p in page_interaction_problems(bad_idx))
    no_check = MW_OK.replace('class="mw-check"', 'class="other"')
    assert any("mw-check" in p for p in page_interaction_problems(no_check))


def test_fill_blanks_contract():
    assert page_interaction_problems(FB_OK) == []
    empty = FB_OK.replace('data-answers="spread"', 'data-answers=""')
    assert any("data-answers" in p and "空" in p for p in page_interaction_problems(empty))
    no_check = FB_OK.replace('class="fb-check"', 'class="other"')
    assert any("fb-check" in p for p in page_interaction_problems(no_check))
    no_blank = FB_OK.replace('<span class="fb-blank" data-answers="spread"></span>', "spread")
    assert any("fb-blank" in p for p in page_interaction_problems(no_blank))


def test_sort_paragraphs_contract():
    assert page_interaction_problems(SP_OK) == []
    bad_orders = SP_OK.replace('data-order="3"', 'data-order="4"')
    assert any("data-order" in p for p in page_interaction_problems(bad_orders))
    no_check = SP_OK.replace('class="sp-check"', 'class="other"')
    assert any("sp-check" in p for p in page_interaction_problems(no_check))
    single = SP_OK.replace('<li class="sp-item" data-order="2">Levi Strauss arrived in San Francisco.</li>', "")
    single = single.replace('<li class="sp-item" data-order="3">Miners asked for sturdy trousers.</li>', "")
    assert any("2 个" in p for p in page_interaction_problems(single))


def test_exercise_components_counted_as_interaction_types():
    types = page_interaction_types(MW_OK + FB_OK + SP_OK)
    assert {"mark-words", "fill-blanks", "sort-paragraphs"} <= types
    # 三组件一页即可满足多样性门槛
    pages = [SimpleNamespace(html=MW_OK + FB_OK + SP_OK)]
    out, summary = run_interaction_check(
        pages, blueprint=[{"kind": "language_focus"}], regen_page=lambda i, pg, pr: None
    )
    assert summary["diversity_ok"] is True and len(summary["types_found"]) >= 3


def test_skeleton_has_exercise_component_hooks():
    from app.services.courseware_llm_generator import _load_skeleton

    html = _load_skeleton()
    for hook in (".mark-words", ".fill-blanks", ".sort-paragraphs", ".mw-check", ".fb-check", ".sp-check", "data-answer", "data-answers", "data-order", "oe-shake"):
        assert hook in html, f"骨架缺少练习组件钩子 {hook}"
