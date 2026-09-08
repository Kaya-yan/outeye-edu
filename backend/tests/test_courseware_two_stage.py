"""③ 两阶段 HTML 课件测试：段落切片 / 长难句加权 / 难词词干归属 / 蓝图校验与回退 / 逐页生成 / 进度文案"""

import json

import pytest

from app.services.courseware_llm_generator import (
    MAX_BLUEPRINT_PAGES,
    _fallback_blueprint,
    _generate_one_page,
    _long_sentence_score,
    _normalize_blueprint,
    _page_progress_label,
    _plan_blueprint,
    _simple_stem,
    _slice_analysis,
    _split_paragraphs,
    _word_in_paragraph,
    generate_html_courseware,
)
from app.services.prompt_manager import render_prompt


# ---- 确定性切片 ----


def test_split_paragraphs_blank_line_split_and_merge():
    text = (
        "Para one has enough words to count as a real paragraph here.\n\n"
        "Short.\n\n"
        "Para two also has enough words for the splitter to keep it alone."
    )
    paras = _split_paragraphs(text)
    assert len(paras) == 2
    assert paras[0].startswith("Para one") and paras[0].endswith("Short.")
    assert paras[1].startswith("Para two")


def test_simple_stem_variants():
    assert _simple_stem("Spreading") == "spread"
    assert _simple_stem("symbols") == "symbol"
    assert _simple_stem("studies") == "study"
    assert _simple_stem("sturdy") == "sturdy"


def test_word_in_paragraph_case_and_inflection():
    tokens = "This sturdy American symbol has now spread throughout the world".split()
    assert _word_in_paragraph("Spread", tokens)
    assert _word_in_paragraph("spreading", tokens)
    assert _word_in_paragraph("symbols", tokens)
    assert not _word_in_paragraph("dollar", tokens)


def test_long_sentence_score_weights_clause_markers():
    plain = " ".join(["word"] * 16) + "."
    heavy = "The fact that students who read widely write better is known."
    assert _long_sentence_score(heavy) > _long_sentence_score(plain)


def test_slice_analysis_assigns_words_and_long_sentences():
    p1 = "This is a short plain paragraph with enough words inside."
    p2 = (
        "The symbol which has now spread throughout most of the world is not the dollar "
        "but a simple pair of blue jeans that almost everybody wears today."
    )
    slices = _slice_analysis(
        [p1, p2],
        {"vocabulary": {"difficult_words": [{"word": "spread"}, {"word": "DOLLAR"}]}},
    )
    assert [s["index"] for s in slices] == [1, 2]
    assert slices[0]["difficult_words"] == [] and slices[0]["long_sentences"] == []
    assert "spread" in slices[1]["difficult_words"] and "DOLLAR" in slices[1]["difficult_words"]
    assert slices[1]["long_sentences"] and "which" in slices[1]["long_sentences"][0]


# ---- 蓝图硬校验 ----


def test_normalize_blueprint_enforces_cover_summary_and_para_types():
    pages, reason = _normalize_blueprint({"pages": [
        {"kind": "agenda", "title": "目标", "intent": "i", "para": None},
        {"kind": "deep_reading", "title": "第1段", "intent": "i", "para": 1},
        {"kind": "deep_reading", "title": "第2段", "intent": "i", "para": [2]},
        {"kind": "bogus_kind", "title": "x", "intent": "i", "para": 1},
    ]}, 2)
    assert reason == "" and pages is not None
    assert pages[0]["kind"] == "cover" and pages[-1]["kind"] == "summary"
    assert [p["kind"] for p in pages[1:4]] == ["agenda", "deep_reading", "deep_reading"]
    assert pages[2]["para"] == [1] and pages[3]["para"] == [2]


def test_normalize_blueprint_rejects_missing_para_coverage():
    pages, reason = _normalize_blueprint({"pages": [
        {"kind": "deep_reading", "title": "d", "intent": "i", "para": 1},
    ]}, 3)
    assert pages is None and "覆盖" in reason and "2" in reason


def test_normalize_blueprint_accepts_paired_anatomy_and_lang_points():
    pages, reason = _normalize_blueprint({"pages": [
        {"kind": "text_anatomy", "title": "第1段原文解剖", "intent": "i", "para": 1},
        {"kind": "lang_points", "title": "第1段语言点", "intent": "i", "para": 1},
    ]}, 1)
    assert reason == "" and pages is not None
    assert [p["kind"] for p in pages] == ["cover", "text_anatomy", "lang_points", "summary"]
    assert pages[1]["para"] == [1] and pages[2]["para"] == [1]


def test_normalize_blueprint_lang_points_alone_does_not_cover_paras():
    # 覆盖判定只认解剖类页型：仅语言点页锚定全部段落仍判漏段
    pages, reason = _normalize_blueprint({"pages": [
        {"kind": "lang_points", "title": "第1段语言点", "intent": "i", "para": 1},
        {"kind": "lang_points", "title": "第2段语言点", "intent": "i", "para": 2},
    ]}, 2)
    assert pages is None and "覆盖" in reason


def test_normalize_blueprint_truncates_to_25_keeping_priority():
    specs = [{"kind": "interaction", "title": f"x{i}", "intent": "i", "para": None} for i in range(24)]
    specs.append({"kind": "deep_reading", "title": "d", "intent": "i", "para": 1})
    pages, reason = _normalize_blueprint({"pages": specs}, 1)
    assert reason == "" and len(pages) == MAX_BLUEPRINT_PAGES
    assert pages[0]["kind"] == "cover" and pages[-1]["kind"] == "summary"
    assert any(p["kind"] == "deep_reading" for p in pages)


def test_fallback_blueprint_covers_all_paragraphs_within_cap():
    slices = [
        {"index": i, "preview": "p", "word_count": 10, "difficult_words": ["w"], "long_sentences": []}
        for i in range(1, 31)
    ]
    pages = _fallback_blueprint(slices)
    covered = {x for p in pages if p["kind"] == "text_anatomy" for x in p["para"]}
    assert covered == set(range(1, 31))
    assert len(pages) <= MAX_BLUEPRINT_PAGES


def test_fallback_blueprint_pairs_anatomy_with_lang_points_on_same_para():
    slices = [{"index": 1, "preview": "p", "word_count": 10, "difficult_words": ["w"], "long_sentences": []}]
    pages = _fallback_blueprint(slices)
    assert [p["kind"] for p in pages] == [
        "cover", "agenda", "vocab", "text_anatomy", "lang_points", "interaction", "summary",
    ]
    assert pages[3]["para"] == [1] and pages[4]["para"] == [1]


def test_page_progress_label_carries_page_type():
    assert _page_progress_label({"kind": "deep_reading", "para": [3]}) == "第3段精讲页"
    assert _page_progress_label({"kind": "deep_reading", "para": [2, 3]}) == "第2-3段精讲页"
    assert _page_progress_label({"kind": "text_anatomy", "para": [3]}) == "第3段原文解剖页"
    assert _page_progress_label({"kind": "lang_points", "para": [2, 3]}) == "第2-3段语言点页"
    assert _page_progress_label({"kind": "agenda", "para": None}) == "目标页"


# ---- 规划器 ----


class _MiniGen:
    def __init__(self, *replies):
        self.replies = list(replies)
        self.calls = 0

    def _generate_with_api(self, messages):
        self.calls += 1
        return self.replies.pop(0), {}


def _planner_json(n_paras=2, accent="#35507a"):
    pages = [
        {"kind": "cover", "title": "", "intent": "建立情境", "para": None},
        {"kind": "vocab", "title": "词汇预教", "intent": "预教难点词", "para": None},
    ]
    pages += [{"kind": "deep_reading", "title": f"第{i}段精讲", "intent": f"细读第{i}段", "para": i} for i in range(1, n_paras + 1)]
    pages.append({"kind": "summary", "title": "总结", "intent": "回收", "para": None})
    return "```json\n" + json.dumps({"accent": accent, "pages": pages, "notes": "n"}, ensure_ascii=False) + "\n```"


_PLAN_KW = dict(
    title="T",
    plan={"activity_designs": [], "objectives": [{"text": "read"}]},
    analysis={},
    slices=[
        {"index": 1, "preview": "p1", "word_count": 20, "difficult_words": ["spread"], "long_sentences": []},
        {"index": 2, "preview": "p2", "word_count": 20, "difficult_words": [], "long_sentences": []},
    ],
    language_name="英语",
    duration_minutes=45,
    course_type="精读",
    teaching_intent=None,
)


def test_planner_parses_llm_json_first_try():
    gen = _MiniGen(_planner_json())
    pages, accent, source, note = _plan_blueprint(gen, **_PLAN_KW)
    assert source == "llm" and note == "" and accent == "#35507a" and gen.calls == 1
    assert [p["kind"] for p in pages][:3] == ["cover", "vocab", "deep_reading"]


def test_planner_retries_then_succeeds():
    gen = _MiniGen("这不是蓝图。", _planner_json())
    pages, accent, source, note = _plan_blueprint(gen, **_PLAN_KW)
    assert source == "llm" and gen.calls == 2


def test_planner_two_failures_fall_back_to_deterministic():
    gen = _MiniGen("垃圾输出", "还是垃圾")
    pages, accent, source, note = _plan_blueprint(gen, **_PLAN_KW)
    assert source == "fallback" and "校验" in note
    covered = {x for p in pages if p["kind"] == "text_anatomy" for x in p["para"]}
    assert covered == {1, 2}


# ---- 逐页生成 ----


DEEP_BODY = (
    '<div class="kicker">课文精讲 · 第 1 段</div>'
    "<h2>Deep Reading</h2>"
    '<div class="page-focus">'
    '<blockquote class="para-original"><p>The story with a <mark class="kw">symbol</mark> works well here in the paragraph.</p>'
    "<footer>—— Para. 1</footer></blockquote>"
    '<div class="sentence-anatomy">'
    '<p class="anatomy-sentence"><span class="cl cl-core">This is the story</span> <span class="cl cl-mod">of a symbol</span>.</p>'
    '<ul class="anatomy-legend"><li><span class="cl cl-core">■</span> 主干：主系表结构</li></ul>'
    "</div>"
    '<div class="sent-walk"><details><summary>句 1：This is the story.</summary><p>讲解文字。</p></details></div>'
    "</div>"
)

BAD_BODY = (
    '<div class="page-focus"><p style="color:#ff0000">raw color here</p></div>'
    '<div class="page-focus"></div>'
)

_SPEC = {"kind": "deep_reading", "title": "第1段精讲", "intent": "细读第1段", "para": [1]}
_PARA = "The story of a sturdy American symbol which has now spread throughout most of the world."


def _page_kwargs():
    return dict(
        paragraphs=[_PARA],
        slices=_slice_analysis([_PARA], {}),
        title="T",
        plan={"activity_designs": [], "objectives": [{"text": "read"}]},
        analysis={},
        text=_PARA,
        language_name="英语",
        text_level="B1",
        student_level="B1",
        duration_minutes=45,
        course_type="精读",
        class_size=30,
        native_language="中文",
        components=[],
        theme=None,
        teaching_intent=None,
    )


def _page_reply(body=DEEP_BODY, page_no=1, title="第1段精讲"):
    return f"```html\n<!--page: {page_no} | {title}-->\n<!--intent: 细读第{page_no}段-->\n{body}\n```\n"


def _run_one_page(*replies):
    gen = _MiniGen(*replies)
    system_prompt, _ = render_prompt("courseware_html_page_v2")
    page, info = _generate_one_page(gen, system_prompt, _SPEC, _page_kwargs(), 1, 6, "前一页「词汇预教」，后一页「第2段精讲」")
    return gen, page, info


def test_one_page_happy_path_no_regen():
    gen, page, info = _run_one_page(_page_reply())
    assert info == {"regens": 0, "sanitized": False, "stub": False} and gen.calls == 1
    assert "sentence-anatomy" in page.html and page.intent == "细读第1段"


def test_one_page_bad_then_fixed_regen():
    gen, page, info = _run_one_page(_page_reply(body=BAD_BODY), _page_reply())
    assert info["regens"] == 1 and not info["sanitized"]
    assert "page-focus" in page.html and "#ff0000" not in page.html


def test_one_page_persistent_failure_sanitizes():
    gen, page, info = _run_one_page(_page_reply(body=BAD_BODY), _page_reply(body=BAD_BODY), _page_reply(body=BAD_BODY))
    assert info["sanitized"] is True and "#ff0000" not in page.html


def test_one_page_no_html_block_uses_stub():
    gen, page, info = _run_one_page("我直接用文字回答，没有代码块。")
    assert info["stub"] is True and "程序兜底" in page.html and "page-focus" in page.html


def test_page_prompt_contains_anchor_and_defense():
    from app.services.teacher_intent import DEFENSE_NOTE

    from app.services.courseware_llm_generator import _build_page_prompt

    prompt = _build_page_prompt(
        {"kind": "deep_reading", "title": "第1段精讲", "intent": "细读", "para": [1]},
        page_no=2,
        total=6,
        context_nav="前一页「词汇预教」，后一页「第2段精讲」",
        **_page_kwargs() | {"teaching_intent": "侧重长难句"},
    )
    assert "锚定第 1 段" in prompt and _PARA in prompt
    assert "<teacher_requirements>" in prompt and "侧重长难句" in prompt and DEFENSE_NOTE in prompt
    assert "${" not in prompt  # 占位符全部替换


# ---- 端到端（fake LLM，含并发逐页与进度文案） ----


class _FakeRAG:
    use_api = True
    replies: list = []

    def __init__(self, **kwargs):
        pass

    def _generate_with_api(self, messages):
        reply = type(self).replies.pop(0) if type(self).replies else _page_reply()
        return reply, {}


def _plan(n_activities: int = 4) -> dict:
    return {
        "activity_designs": [
            {"name": f"环节{i}", "duration": "10 分钟", "objective": "o", "steps": "s"}
            for i in range(1, n_activities + 1)
        ],
        "objectives": [{"text": "read"}],
    }


@pytest.fixture()
def fake_llm(monkeypatch):
    def install(*replies: str):
        _FakeRAG.replies = list(replies)
        _FakeRAG.use_api = True
        monkeypatch.setattr("app.services.rag.RAGGenerator", _FakeRAG)

    return install


def _two_stage_replies(n_paras: int = 1, accent: str = "#35507a"):
    planner = _planner_json(n_paras=n_paras, accent=accent)
    n_pages = 2 + n_paras + 1  # cover/vocab + 逐段精讲 + summary（planner_json 无 interaction）
    return [planner] + [_page_reply() for _ in range(n_pages)]


def _run_generate(theme=None, progress=None):
    return generate_html_courseware(
        title="测试课件",
        plan=_plan(),
        analysis={},
        text="A" * 200,
        theme=theme,
        progress_cb=progress,
    )


def test_generate_two_stage_end_to_end(fake_llm):
    fake_llm(*_two_stage_replies())
    result = _run_generate()
    assert result.fallback is False
    assert result.self_check["generation_mode"] == "two_stage"
    assert result.self_check["pages_count"] == 4
    assert result.self_check["blueprint"]["source"] == "llm"
    assert result.self_check["accent"] == "#35507a"
    assert result.html.count('<section class="page"') == 4
    assert "anatomy-sentence" in result.html
    # 蓝图随产物落库，供 S4 编辑复用
    bp = result.editor_schema["meta"]["source_meta"]["page_blueprint"]
    assert [p["kind"] for p in bp] == ["cover", "vocab", "deep_reading", "summary"]


def test_generate_reports_typed_progress(fake_llm):
    messages: list = []
    fake_llm(*_two_stage_replies())
    result = _run_generate(progress=messages.append)
    assert any("正在规划课件页面结构" in m for m in messages)
    assert any(m == "正在生成：第1段精讲页（3/4）" for m in messages)
    assert any(m.endswith("（4/4）") for m in messages)
    assert result.fallback is False


def test_generate_planner_failure_uses_deterministic_blueprint(fake_llm):
    fake_llm("垃圾", "还是垃圾", *[_page_reply() for _ in range(6)])
    result = _run_generate()
    assert result.fallback is False
    assert result.self_check["blueprint"]["source"] == "fallback"
    assert result.self_check["blueprint"]["note"]
    assert result.self_check["pages_count"] == len(result.editor_schema["meta"]["source_meta"]["page_blueprint"])


def test_generate_no_api_falls_back_to_bootstrap(fake_llm, monkeypatch):
    _FakeRAG.use_api = False
    monkeypatch.setattr("app.services.rag.RAGGenerator", _FakeRAG)
    result = _run_generate()
    assert result.fallback is True
    assert result.self_check.get("prompt_version") == "fallback"


# ---- 任务A2/A3：交互自检接线与溢出提示交付 ----


def test_generate_runs_interaction_check_and_records_summary(fake_llm):
    fake_llm(*_two_stage_replies())
    result = _run_generate()
    ix = result.self_check["interaction_check"]
    assert ix["enabled"] is True and ix["min_types"] == 3
    assert "anatomy" in ix["types_found"] and "sent-walk" in ix["types_found"]
    assert ix["structural_problem_pages"] == {}


def test_generate_interaction_check_disabled(fake_llm, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "INTERACTION_CHECK_ENABLED", False)
    fake_llm(*_two_stage_replies())
    result = _run_generate()
    assert result.self_check["interaction_check"] == {"enabled": False}
    assert result.self_check["pages_count"] == 4


def test_generate_interaction_check_error_degrades(fake_llm, monkeypatch):
    def _boom(*args, **kwargs):
        raise RuntimeError("ix boom")

    monkeypatch.setattr("app.services.courseware_interaction_check.run_interaction_check", _boom)
    fake_llm(*_two_stage_replies())
    result = _run_generate()
    ix = result.self_check["interaction_check"]
    assert ix["enabled"] is True and "ix boom" in ix["error"]


def test_generate_overflow_notices_delivered_to_source_meta(fake_llm, monkeypatch):
    def _fake_visual_qc(pages, **kwargs):
        return list(pages), {"overflow": {"still_overflowing": {"2": 12}}}

    monkeypatch.setattr("app.services.courseware_visual_qc.run_visual_qc", _fake_visual_qc)
    fake_llm(*_two_stage_replies())
    result = _run_generate()
    notices = result.editor_schema["meta"]["source_meta"]["overflow_notices"]
    assert notices == [{"page": 2, "pct": 12, "note": "第 2 页内容较多（超页约 12%），建议在编辑器中精简"}]


def test_generate_no_overflow_notices_when_gate_clean(fake_llm, monkeypatch):
    def _fake_visual_qc(pages, **kwargs):
        return list(pages), {"overflow": {"still_overflowing": {}}}

    monkeypatch.setattr("app.services.courseware_visual_qc.run_visual_qc", _fake_visual_qc)
    fake_llm(*_two_stage_replies())
    result = _run_generate()
    assert result.editor_schema["meta"]["source_meta"].get("overflow_notices") is None
