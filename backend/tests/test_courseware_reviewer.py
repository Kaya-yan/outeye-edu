"""S5 教研员评审测试：JSON 解析 / 指数退避 / fail 带意见重写并保留最高分 / 异常保留原稿 / 开关降级 / 端到端摘要"""

import json

import pytest

from app.services.courseware_llm_generator import _ContentPage, _slice_analysis, generate_html_courseware
from app.services.courseware_page_reviewer import (
    MAX_REVIEW_REWRITES,
    REVIEW_PASS_SCORE,
    _call_with_backoff,
    _parse_review,
    _review_one_page,
    review_pages,
)


# ---- 解析与退避 ----


def test_parse_review_accepts_fenced_and_raw_json():
    fenced = '```json\n{"score": 8.5, "verdict": "pass", "problems": [], "suggestions": ["x"]}\n```'
    raw = '{"score": 6, "verdict": "fail", "problems": ["p1"], "suggestions": []}'
    assert _parse_review(fenced)["score"] == 8.5
    assert _parse_review(raw)["verdict"] == "fail"


def test_parse_review_corrects_verdict_and_clips():
    data = _parse_review('{"score": 5, "verdict": "pass", "problems": [' + ",".join(f'"p{i}"' for i in range(9)) + ']}')
    assert data["verdict"] == "fail"  # score 与 verdict 不一致以 score 为准
    assert len(data["problems"]) == 6
    assert _parse_review("我觉得这页不错") is None
    assert _parse_review('{"score": "high"}') is None
    clamped = _parse_review('{"score": 42}')
    assert clamped["score"] == 10.0


def test_call_with_backoff_retries_transient_failures(monkeypatch):
    from app.services import courseware_page_reviewer as mod

    monkeypatch.setattr(mod.time, "sleep", lambda s: None)

    class Flaky:
        calls = 0

        def _generate_with_api(self, messages):
            type(self).calls += 1
            if self.calls < 3:
                raise RuntimeError("timeout")
            return "ok", {}

    assert _call_with_backoff(Flaky(), [{"role": "user", "content": "x"}]) == "ok"
    assert Flaky.calls == 3

    class Dead:
        def _generate_with_api(self, messages):
            raise RuntimeError("down")

    with pytest.raises(RuntimeError):
        _call_with_backoff(Dead(), [{"role": "user", "content": "x"}])


# ---- 单页复核：重写与择优 ----


class _MiniGen:
    def __init__(self, *replies):
        self.replies = list(replies)

    def _generate_with_api(self, messages):
        return self.replies.pop(0), {}


def _review_reply(score, verdict=None, problems=(), suggestions=()):
    v = verdict or ("pass" if score >= REVIEW_PASS_SCORE else "fail")
    return "```json\n" + json.dumps(
        {"score": score, "verdict": v, "problems": list(problems), "suggestions": list(suggestions)},
        ensure_ascii=False,
    ) + "\n```"


_ORIG_BODY = (
    '<div class="kicker">课文精讲 · 第 1 段</div><h2>Deep Reading</h2>'
    '<div class="page-focus"><p>Original page content with a mark here.</p></div>'
)
_REWRITTEN_BODY = (
    '<div class="kicker">课文精讲 · 第 1 段</div><h2>Deep Reading</h2>'
    '<div class="page-focus"><p>REWRITTEN content fixing the reviewer problems.</p></div>'
)


def _html_reply(body, title="第1段精讲"):
    return f"```html\n<!--page: 1 | {title}-->\n<!--intent: 细读第1段-->\n{body}\n```\n"


def _page_kwargs():
    para = "The story of a sturdy American symbol which has now spread throughout most of the world."
    return dict(
        paragraphs=[para],
        slices=_slice_analysis([para], {}),
        title="T",
        plan={"activity_designs": [], "objectives": [{"text": "read"}]},
        analysis={},
        text=para,
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


_SPEC = {"kind": "deep_reading", "title": "第1段精讲", "intent": "细读第1段", "para": [1]}


def _run_review(*replies):
    gen = _MiniGen(*replies)
    page = _ContentPage(title="第1段精讲", intent="细读第1段", html=_ORIG_BODY)
    return _review_one_page(gen, _SPEC, page, _page_kwargs(), 1, 6, "前一页「词汇预教」，后一页「第2段精讲」")


def test_fail_then_rewrite_pass_adopts_rewritten_page():
    page, stats = _run_review(
        _review_reply(5.0, problems=["缺衔接点评"]),
        _html_reply(_REWRITTEN_BODY),
        _review_reply(9.0),
    )
    assert "REWRITTEN" in page.html
    assert stats["rewrites"] == 1 and stats["score"] == 9.0 and stats["verdict"] == "pass"


def test_rewrite_not_better_keeps_original_and_caps_rounds():
    page, stats = _run_review(
        _review_reply(6.0, problems=["偏浅"]),
        _html_reply(_REWRITTEN_BODY),
        _review_reply(5.0, problems=["仍偏浅"]),
        _html_reply(_REWRITTEN_BODY),
        _review_reply(5.5, problems=["仍偏浅"]),
    )
    assert "REWRITTEN" not in page.html  # 改写未超原分 → 保留原稿
    assert stats["rewrites"] == MAX_REVIEW_REWRITES and stats["score"] == 6.0


def test_unparseable_review_marks_unreviewed_without_rewrite():
    page, stats = _run_review("这页挺好的，我打九分。")
    assert "REWRITTEN" not in page.html and stats["verdict"] == "unreviewed" and stats["rewrites"] == 0


def test_pass_first_time_no_rewrite():
    page, stats = _run_review(_review_reply(8.0))
    assert stats["rewrites"] == 0 and stats["score"] == 8.0


# ---- review_pages：stub 跳过 + 摘要 ----


def test_review_pages_skips_stubs_and_builds_summary():
    gen = _MiniGen(_review_reply(9.0))
    specs = [
        {"kind": "cover", "title": "封面", "intent": "i", "para": None},
        {"kind": "summary", "title": "总结", "intent": "i", "para": None},
    ]
    pages = [
        _ContentPage(title="封面", intent="i", html='<div class="page-focus"><p>a</p></div>'),
        _ContentPage(title="总结", intent="i", html='<div class="page-focus"><p>b</p></div>'),
    ]
    messages: list = []
    out, summary = review_pages(gen, specs, _page_kwargs(), pages, {1: {"stub": True}}, messages.append)
    assert summary["pages"][1]["verdict"] == "skipped_stub"
    assert summary["pages"][0]["score"] == 9.0
    assert summary["avg_score"] == 9.0  # stub 页不计入均分
    assert summary["rewritten_pages"] == [] and summary["still_failing_pages"] == []
    assert any("正在复核：第" in m for m in messages)
    assert len(out) == 2


# ---- 端到端（fake LLM）：评审层接入与开关降级 ----


class _FakeRAG:
    use_api = True
    replies: list = []

    def __init__(self, **kwargs):
        pass

    def _generate_with_api(self, messages):
        reply = type(self).replies.pop(0) if type(self).replies else _html_reply(_ORIG_BODY)
        return reply, {}


@pytest.fixture()
def fake_llm(monkeypatch):
    def install(*replies: str):
        _FakeRAG.replies = list(replies)
        _FakeRAG.use_api = True
        monkeypatch.setattr("app.services.rag.RAGGenerator", _FakeRAG)

    return install


def _planner_json(n_paras=1, accent="#35507a"):
    pages = [
        {"kind": "cover", "title": "", "intent": "建立情境", "para": None},
        {"kind": "vocab", "title": "词汇预教", "intent": "预教难点词", "para": None},
    ]
    pages += [{"kind": "deep_reading", "title": f"第{i}段精讲", "intent": f"细读第{i}段", "para": i} for i in range(1, n_paras + 1)]
    pages.append({"kind": "summary", "title": "总结", "intent": "回收", "para": None})
    return "```json\n" + json.dumps({"accent": accent, "pages": pages, "notes": "n"}, ensure_ascii=False) + "\n```"


def _page_reply(page_no=1):
    body = (
        '<div class="kicker">STAGE</div><h2>Page {no}</h2>'
        '<div class="page-focus"><p>Page body with <mark class="kw">symbol</mark> inside. '
        "This paragraph is long enough to pass the minimum content length check for validation. "
        "It also mentions spread and sturdy words for the anchored paragraph slice.</p></div>"
    ).format(no=page_no)
    return f"```html\n<!--page: {page_no} | P-->\n<!--intent: i-->\n{body}\n```\n"


def _run_generate(progress=None):
    return generate_html_courseware(
        title="测试课件",
        plan={"activity_designs": [], "objectives": [{"text": "read"}]},
        analysis={},
        text="A" * 200,
        progress_cb=progress,
    )


def test_generate_reports_reviewer_summary(fake_llm):
    messages: list = []
    fake_llm(_planner_json(), *[_page_reply() for _ in range(4)], *[_review_reply(9.0) for _ in range(4)])
    result = _run_generate(messages.append)
    assert result.fallback is False
    reviewer = result.self_check["reviewer"]
    assert reviewer["avg_score"] == 9.0
    assert reviewer["rewritten_pages"] == [] and reviewer["still_failing_pages"] == []
    assert any("AI 教研员正在复核页面质量" in m for m in messages)
    assert any("正在复核：第 1 页（" in m for m in messages)


def test_generate_reviewer_disabled_skips_layer(fake_llm, monkeypatch):
    monkeypatch.setattr("app.core.config.settings.PAGE_REVIEWER_ENABLED", False)
    fake_llm(_planner_json(), *[_page_reply() for _ in range(4)])
    result = _run_generate()
    assert result.self_check["reviewer"] == {"enabled": False}
    assert _FakeRAG.replies == []  # 无复核调用，fake 回复恰好耗尽


def test_generate_reviewer_garbage_replies_degrade_gracefully(fake_llm):
    # 复核回复全部不可解析 → 记 unreviewed，课件照常产出
    fake_llm(_planner_json(), *[_page_reply() for _ in range(4)], *["看不懂但应该不错" for _ in range(4)])
    result = _run_generate()
    assert result.fallback is False
    reviewer = result.self_check["reviewer"]
    assert sorted(reviewer["unreviewed_pages"]) == [1, 2, 3, 4]
    assert reviewer["avg_score"] is None
