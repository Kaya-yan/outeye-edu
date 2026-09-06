"""S6 视觉质检测试：问题页重生成一轮 / 未配 key、超时、截图失败降级 / 开关与端到端接入"""

import json

import pytest

from app.services import courseware_visual_qc as vqc
from app.services.courseware_llm_generator import _ContentPage, generate_html_courseware


def _pages(n=3):
    return [
        _ContentPage(title=f"P{i + 1}", intent="i", html=f'<div class="page-focus"><p>page {i + 1}</p></div>')
        for i in range(n)
    ]


def _blueprint(n=3):
    return [{"kind": "deep_reading", "title": f"P{i + 1}", "intent": "i", "para": 1} for i in range(n)]


def _with_key(monkeypatch):
    monkeypatch.setattr("app.core.config.settings.VISION_API_KEY", "sk-test")


def test_no_vision_key_skips_layer(monkeypatch):
    monkeypatch.setattr("app.core.config.settings.VISION_API_KEY", "")
    pages = _pages()
    out, summary = vqc.run_visual_qc(
        pages, blueprint=_blueprint(), make_doc=lambda pg: pg.html, regen_page=lambda i, p, pr: None
    )
    assert summary["skipped"] == "未配置 VISION_API_KEY"
    assert out == pages and summary["issue_pages"] == []


def test_issue_page_regenerated_once(monkeypatch):
    _with_key(monkeypatch)
    monkeypatch.setattr(vqc, "_screenshot_pages", lambda docs, deadline: ([b"s1", b"s2", b"s3"], None))
    monkeypatch.setattr(vqc, "_vl_check", lambda shot, prompt: (["文字溢出卡片右边界"] if shot == b"s2" else []))
    calls: list = []

    def regen(i, pg, problems):
        calls.append((i, problems))
        return _ContentPage(title=pg.title, intent=pg.intent, html='<div class="page-focus"><p>FIXED</p></div>')

    messages: list = []
    out, summary = vqc.run_visual_qc(
        _pages(), blueprint=_blueprint(), make_doc=lambda pg: pg.html, regen_page=regen, progress_cb=messages.append
    )
    assert calls == [(1, ["文字溢出卡片右边界"])]  # 只重生成问题页一轮
    assert "FIXED" in out[1].html and "page 1" in out[0].html and "page 3" in out[2].html
    assert summary["checked_pages"] == [1, 2, 3]
    assert summary["issue_pages"] == [2] and summary["regenerated_pages"] == [2]
    assert summary["issues"]["2"] == ["文字溢出卡片右边界"]
    assert any("发现 1 处视觉问题" in m for m in messages)


def test_vl_unavailable_marks_unchecked(monkeypatch):
    _with_key(monkeypatch)
    monkeypatch.setattr(vqc, "_screenshot_pages", lambda docs, deadline: ([b"s1", b"s2"], None))
    monkeypatch.setattr(vqc, "_vl_check", lambda shot, prompt: None)
    pages = _pages(2)
    out, summary = vqc.run_visual_qc(
        pages, blueprint=_blueprint(2), make_doc=lambda pg: pg.html, regen_page=lambda i, p, pr: None
    )
    assert summary["unchecked_pages"] == [1, 2] and summary["checked_pages"] == []
    assert summary["issue_pages"] == [] and out == pages


def test_deadline_breach_skips_regen(monkeypatch):
    _with_key(monkeypatch)
    monkeypatch.setattr(vqc, "_screenshot_pages", lambda docs, deadline: ([b"s1"], None))
    monkeypatch.setattr(vqc, "_vl_check", lambda shot, prompt: ["对比度不足"])
    pages = _pages(1)
    out, summary = vqc.run_visual_qc(
        pages, blueprint=_blueprint(1), make_doc=lambda pg: pg.html,
        regen_page=lambda i, p, pr: (_ for _ in ()).throw(AssertionError("超时后不应重生成")),
        budget_seconds=0.0,
    )
    assert summary["issue_pages"] == [1] and summary["regenerated_pages"] == []
    assert summary["deadline_hit"] is True and out == pages


def test_screenshot_error_degrades_gracefully(monkeypatch):
    _with_key(monkeypatch)
    monkeypatch.setattr(vqc, "_screenshot_pages", lambda docs, deadline: (None, "chromium 不可用"))
    pages = _pages(2)
    out, summary = vqc.run_visual_qc(
        pages, blueprint=_blueprint(2), make_doc=lambda pg: pg.html, regen_page=lambda i, p, pr: None
    )
    assert summary["error"] == "chromium 不可用"
    assert out == pages and summary["issue_pages"] == []


def test_screenshot_exception_degrades_gracefully(monkeypatch):
    _with_key(monkeypatch)

    def boom(docs, deadline):
        raise RuntimeError("playwright not installed")

    monkeypatch.setattr(vqc, "_screenshot_pages", boom)
    pages = _pages(1)
    out, summary = vqc.run_visual_qc(
        pages, blueprint=_blueprint(1), make_doc=lambda pg: pg.html, regen_page=lambda i, p, pr: None
    )
    assert "error" in summary and out == pages


def test_regen_exception_keeps_original(monkeypatch):
    _with_key(monkeypatch)
    monkeypatch.setattr(vqc, "_screenshot_pages", lambda docs, deadline: ([b"s1"], None))
    monkeypatch.setattr(vqc, "_vl_check", lambda shot, prompt: ["元素重叠"])

    def bad_regen(i, pg, problems):
        raise RuntimeError("rewrite failed")

    pages = _pages(1)
    out, summary = vqc.run_visual_qc(pages, blueprint=_blueprint(1), make_doc=lambda pg: pg.html, regen_page=bad_regen)
    assert out == pages and summary["issue_pages"] == [1] and summary["regenerated_pages"] == []


# ---- 端到端（fake LLM + 假截图/VL） ----


class _FakeRAG:
    use_api = True
    replies: list = []

    def __init__(self, **kwargs):
        pass

    def _generate_with_api(self, messages):
        reply = type(self).replies.pop(0) if type(self).replies else "```html\n<!--page: 1 | P-->\n<!--intent: i-->\n<div class=\"page-focus\"><p>fallback body long enough to pass the content length validation easily.</p></div>\n```\n"
        return reply, {}


@pytest.fixture()
def fake_llm(monkeypatch):
    def install(*replies: str):
        _FakeRAG.replies = list(replies)
        _FakeRAG.use_api = True
        monkeypatch.setattr("app.services.rag.RAGGenerator", _FakeRAG)

    return install


def _planner_json(n_paras=1):
    pages = [
        {"kind": "cover", "title": "", "intent": "i", "para": None},
        {"kind": "vocab", "title": "v", "intent": "i", "para": None},
    ]
    pages += [{"kind": "deep_reading", "title": "d", "intent": "i", "para": i} for i in range(1, n_paras + 1)]
    pages.append({"kind": "summary", "title": "s", "intent": "i", "para": None})
    return "```json\n" + json.dumps({"accent": "#35507a", "pages": pages}) + "\n```"


def _review_reply():
    return '```json\n{"score": 9.0, "verdict": "pass", "problems": [], "suggestions": []}\n```'


def _run_generate():
    return generate_html_courseware(
        title="测试课件",
        plan={"activity_designs": [], "objectives": [{"text": "read"}]},
        analysis={},
        text="A" * 200,
    )


def test_generate_visual_qc_end_to_end_all_clean(fake_llm, monkeypatch):
    _with_key(monkeypatch)
    monkeypatch.setattr(vqc, "_screenshot_pages", lambda docs, deadline: ([b"shot"] * 4, None))
    monkeypatch.setattr(vqc, "_vl_check", lambda shot, prompt: [])
    fake_llm(_planner_json(), *["```html\n<!--page: 1 | P-->\n<!--intent: i-->\n<div class=\"page-focus\"><p>" + "body " * 30 + "</p></div>\n```\n" for _ in range(4)], *[_review_reply() for _ in range(4)])
    result = _run_generate()
    assert result.fallback is False
    qc = result.self_check["visual_qc"]
    assert qc["enabled"] is True and qc["checked_pages"] == [1, 2, 3, 4]
    assert qc["issue_pages"] == [] and qc["regenerated_pages"] == []


def test_generate_visual_qc_disabled(fake_llm, monkeypatch):
    monkeypatch.setattr("app.core.config.settings.VISUAL_QC_ENABLED", False)
    fake_llm(_planner_json(), *["```html\n<!--page: 1 | P-->\n<!--intent: i-->\n<div class=\"page-focus\"><p>" + "body " * 30 + "</p></div>\n```\n" for _ in range(4)], *[_review_reply() for _ in range(4)])
    result = _run_generate()
    assert result.self_check["visual_qc"] == {"enabled": False}


def test_generate_visual_qc_issue_page_regenerated(fake_llm, monkeypatch):
    _with_key(monkeypatch)
    fixed_body = "```html\n<!--page: 1 | P-->\n<!--intent: i-->\n<div class=\"page-focus\"><p>REWRITTEN " + "visual fix " * 15 + "</p></div>\n```\n"
    monkeypatch.setattr(vqc, "_screenshot_pages", lambda docs, deadline: ([b"shot"] * 4, None))
    monkeypatch.setattr(vqc, "_vl_check", lambda shot, prompt: (["文字溢出"] if ("精讲" in prompt or "总结" in prompt) else []))
    # VL 视问题页：精讲/总结页报问题 → 重生成回复接在评审回复之后
    fake_llm(
        _planner_json(),
        *["```html\n<!--page: 1 | P-->\n<!--intent: i-->\n<div class=\"page-focus\"><p>" + "body " * 30 + "</p></div>\n```\n" for _ in range(4)],
        *[_review_reply() for _ in range(4)],
        fixed_body,
        fixed_body,
    )
    result = _run_generate()
    assert result.fallback is False
    qc = result.self_check["visual_qc"]
    assert qc["issue_pages"] and qc["regenerated_pages"] == qc["issue_pages"]
    assert "REWRITTEN" in result.html
