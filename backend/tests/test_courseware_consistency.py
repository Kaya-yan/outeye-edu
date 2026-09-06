"""S7 全局一致性审校测试：文本节点替换与词边界 / 结构校验回滚 / 意见存档 / 开关与端到端"""

import json

import pytest

from app.services import courseware_consistency as cc
from app.services.courseware_llm_generator import generate_html_courseware

HTML = (
    "<html><head><title>T</title></head><body>"
    '<section class="page"><div class="page-focus"><p>The rivet tool uses 列维·斯特劳斯 here and there.</p></div></section>'
    '<section class="page"><div class="page-focus"><p>列维·斯特劳斯 again, and symbols of freedom.</p></div></section>'
    "</body></html>"
)


# ---- 替换引擎 ----


def test_replace_only_in_text_nodes():
    html = '<section class="page"><div class="body-class"><p>body text uses body words</p></div></section>'
    new, per, total = cc._replace_in_text_nodes(html, {"body": "segment"})
    assert new.count("segment") == 2
    assert "body-class" in new  # 标签与属性不受影响
    assert per == {"body": 2} and total == 2


def test_word_boundary_latin():
    new, per, total = cc._replace_in_text_nodes("<p>the symbol and symbols</p>", {"symbol": "mark"})
    assert new == "<p>the mark and symbols</p>" and total == 1


def test_structure_ok_guards():
    assert cc._structure_ok(HTML, HTML.replace("列维", "李维"))
    assert not cc._structure_ok(HTML, HTML + '<section class="page">x</section>')
    assert not cc._structure_ok(HTML, HTML + "<script>alert(1)</script>")


def test_pages_digest_covers_pages():
    digest = cc._pages_digest(HTML)
    assert "【第 1 页】" in digest and "【第 2 页】" in digest
    assert "rivet" in digest and "<" not in digest


# ---- 审校流程 ----


class _MiniGen:
    def __init__(self, *replies):
        self.replies = list(replies)

    def _generate_with_api(self, messages):
        return self.replies.pop(0), {}


def _review_reply(terminology=(), notes=()):
    return "```json\n" + json.dumps({
        "terminology": [{"canonical": c, "variants": list(v)} for c, v in terminology],
        "structure_notes": list(notes),
    }, ensure_ascii=False) + "\n```"


def test_run_review_replaces_and_records_notes():
    gen = _MiniGen(_review_reply([("李维·斯特劳斯", ["列维·斯特劳斯"])], ["第 2 页建议补充作业布置"]))
    messages: list = []
    new, summary = cc.run_consistency_review(gen, html=HTML, title="T", progress_cb=messages.append)
    assert "李维·斯特劳斯" in new and "列维·斯特劳斯" not in new
    assert new.count('<section class="page"') == 2
    assert summary["total_replaced"] == 2 and summary["replacements"] == {"列维·斯特劳斯": 2}
    assert summary["structure_notes"] == ["第 2 页建议补充作业布置"]
    assert any("统一了 2 处术语" in m for m in messages)


def test_run_review_rollback_when_structure_breaks(monkeypatch):
    gen = _MiniGen(_review_reply([("李维·斯特劳斯", ["列维·斯特劳斯"])]))

    def bad_replace(html, variants):
        return html + '<section class="page">broken</section>', {"列维·斯特劳斯": 1}, 1

    monkeypatch.setattr(cc, "_replace_in_text_nodes", bad_replace)
    new, summary = cc.run_consistency_review(gen, html=HTML, title="T")
    assert new == HTML and summary["rolled_back"] is True


def test_run_review_unparseable_keeps_html():
    gen = _MiniGen("整体很一致，无需修改。")
    new, summary = cc.run_consistency_review(gen, html=HTML, title="T")
    assert new == HTML and "note" in summary and "structure_notes" not in summary


def test_run_review_exception_returns_original():
    class Dead:
        def _generate_with_api(self, messages):
            raise RuntimeError("down")

    new, summary = cc.run_consistency_review(Dead(), html=HTML, title="T")
    assert new == HTML and "error" in summary


def test_run_review_variant_not_found_notes():
    gen = _MiniGen(_review_reply([("标准词", ["不存在的变体"])]))
    new, summary = cc.run_consistency_review(gen, html=HTML, title="T")
    assert new == HTML and summary["total_replaced"] == 0
    assert "未在课件中命中" in summary["note"]


# ---- 端到端（fake LLM） ----


class _FakeRAG:
    use_api = True
    replies: list = []

    def __init__(self, **kwargs):
        pass

    def _generate_with_api(self, messages):
        reply = type(self).replies.pop(0) if type(self).replies else "```html\nx\n```\n"
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


_PAGE = "```html\n<!--page: 1 | P-->\n<!--intent: i-->\n<div class=\"page-focus\"><p>" + "body word " * 20 + "</p></div>\n```\n"
_REVIEW = '```json\n{"score": 9.0, "verdict": "pass", "problems": [], "suggestions": []}\n```'


def _run_generate():
    return generate_html_courseware(
        title="测试课件",
        plan={"activity_designs": [], "objectives": [{"text": "read"}]},
        analysis={},
        text="A" * 200,
    )


def test_generate_consistency_end_to_end(fake_llm):
    fake_llm(
        _planner_json(),
        *[_PAGE for _ in range(4)],
        *[_REVIEW for _ in range(4)],
        _review_reply([("segment", ["body"])], ["总结页建议补充写作迁移作业"]),
    )
    result = _run_generate()
    assert result.fallback is False
    cr = result.self_check["consistency_review"]
    assert cr["total_replaced"] >= 4 and cr["replacements"] == {"body": cr["total_replaced"]}
    assert cr["structure_notes"] == ["总结页建议补充写作迁移作业"]
    assert "segment" in result.html and ">body" not in result.html
    meta = result.editor_schema["meta"]["source_meta"]["consistency_review"]
    assert meta["structure_notes"] == cr["structure_notes"]


def test_generate_consistency_disabled(fake_llm, monkeypatch):
    monkeypatch.setattr("app.core.config.settings.CONSISTENCY_REVIEW_ENABLED", False)
    fake_llm(_planner_json(), *[_PAGE for _ in range(4)], *[_REVIEW for _ in range(4)])
    result = _run_generate()
    assert result.self_check["consistency_review"] == {"enabled": False}
    assert result.editor_schema["meta"]["source_meta"]["consistency_review"] is None
