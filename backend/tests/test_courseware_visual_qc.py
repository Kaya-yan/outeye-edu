"""S6 视觉质检测试（两相）：溢出硬关卡（几何检测/两轮重生成/仍超保留）+ VL 问题页重生成 / 未配 key、
超时、chromium 缺失降级 / 双开关独立门控 / 骨架 CSS 韧性契约 / 端到端接入"""

import json

import pytest

from app.services import courseware_visual_qc as vqc
from app.services.courseware_llm_generator import _ContentPage, _load_skeleton, generate_html_courseware


def _pages(n=3):
    return [
        _ContentPage(title=f"P{i + 1}", intent="i", html=f'<div class="page-focus"><p>page {i + 1}</p></div>')
        for i in range(n)
    ]


def _blueprint(n=3):
    return [{"kind": "deep_reading", "title": f"P{i + 1}", "intent": "i", "para": 1} for i in range(n)]


def _with_key(monkeypatch):
    monkeypatch.setattr("app.core.config.settings.VISION_API_KEY", "sk-test")


# ---- 相 A：溢出硬关卡 ----


def test_gate_two_rounds_then_keeps_and_records(monkeypatch):
    monkeypatch.setattr("app.core.config.settings.VISION_API_KEY", "")
    seq = [
        ([b"a", b"b", b"c"], [200, 0, 0], None),
        ([b"a1"], [80], None),
        ([b"a2"], [40], None),
    ]
    calls: list = []

    def fake_shot(docs, deadline):
        calls.append(len(docs))
        return seq.pop(0)

    monkeypatch.setattr(vqc, "_screenshot_pages", fake_shot)
    regen_calls: list = []

    def regen(i, pg, problems):
        regen_calls.append((i, problems))
        return _ContentPage(title=pg.title, intent="i", html='<div class="page-focus"><p>slim</p></div>')

    messages: list = []
    out, summary = vqc.run_visual_qc(
        _pages(), blueprint=_blueprint(), make_doc=lambda pg: pg.html, regen_page=regen, progress_cb=messages.append
    )
    of = summary["overflow"]
    assert calls == [3, 1, 1]  # 全量测一次 + 单页复测两次
    assert of["overflow_pages"] == {"1": 28}  # 200/720 ≈ 28%
    assert of["regenerated"] == {"1": 2} and of["still_overflowing"] == {"1": 6}  # 40/720 ≈ 6%
    assert "内容超页约 28%" in regen_calls[0][1][0] and "200px" in regen_calls[0][1][0]
    assert "slim" in out[0].html and "page 2" in out[1].html  # 两轮精简稿被保留
    assert any("超页约" in m for m in messages)
    assert "未配置 VISION_API_KEY" in summary["skipped"]  # 无 key 不影响硬关卡执行


def test_gate_fixed_in_one_round(monkeypatch):
    monkeypatch.setattr("app.core.config.settings.VISION_API_KEY", "")
    seq = [([b"a", b"b"], [150, 0], None), ([b"a1"], [5], None)]
    monkeypatch.setattr(vqc, "_screenshot_pages", lambda docs, deadline: seq.pop(0))
    out, summary = vqc.run_visual_qc(
        _pages(2), blueprint=_blueprint(2), make_doc=lambda pg: pg.html,
        regen_page=lambda i, pg, pr: _ContentPage(title=pg.title, intent="i", html='<div class="page-focus"><p>ok</p></div>'),
    )
    of = summary["overflow"]
    assert of["overflow_pages"] == {"1": 21} and of["regenerated"] == {"1": 1}
    assert of["still_overflowing"] == {} and "ok" in out[0].html


def test_gate_regen_none_keeps_original_and_records(monkeypatch):
    monkeypatch.setattr("app.core.config.settings.VISION_API_KEY", "")
    monkeypatch.setattr(vqc, "_screenshot_pages", lambda docs, deadline: ([b"a"], [300], None))
    pages = _pages(1)
    out, summary = vqc.run_visual_qc(
        pages, blueprint=_blueprint(1), make_doc=lambda pg: pg.html, regen_page=lambda i, p, pr: None
    )
    of = summary["overflow"]
    assert out == pages and of["still_overflowing"] == {"1": 42} and of["regenerated"] == {"1": 1}


def test_gate_respects_deadline_no_regen(monkeypatch):
    monkeypatch.setattr("app.core.config.settings.VISION_API_KEY", "")
    monkeypatch.setattr(vqc, "_screenshot_pages", lambda docs, deadline: ([b"a"], [300], None))
    pages = _pages(1)
    out, summary = vqc.run_visual_qc(
        pages, blueprint=_blueprint(1), make_doc=lambda pg: pg.html,
        regen_page=lambda i, p, pr: (_ for _ in ()).throw(AssertionError("超时后不应重生成")),
        budget_seconds=0.0,
    )
    assert out == pages
    assert summary["overflow"]["overflow_pages"] == {"1": 42}
    assert summary["overflow"]["regenerated"] == {} and summary["overflow"]["still_overflowing"] == {"1": 42}


def test_gate_chromium_missing_recorded_not_silent(monkeypatch):
    monkeypatch.setattr("app.core.config.settings.VISION_API_KEY", "")
    err = "playwright 未安装: No module named 'playwright'"
    monkeypatch.setattr(vqc, "_screenshot_pages", lambda docs, deadline: ([], [], err))
    pages = _pages(2)
    out, summary = vqc.run_visual_qc(
        pages, blueprint=_blueprint(2), make_doc=lambda pg: pg.html, regen_page=lambda i, p, pr: None
    )
    assert out == pages
    assert summary["overflow"]["skipped"] == err
    assert summary["overflow"]["checked_pages"] == []


def test_gate_disabled_by_switch_skips_geometry(monkeypatch):
    _with_key(monkeypatch)
    monkeypatch.setattr(
        vqc, "_screenshot_pages", lambda docs, deadline: ([b"s1", b"s2"], [999, 999], None)
    )
    monkeypatch.setattr(vqc, "_vl_check", lambda shot, prompt: [])
    out, summary = vqc.run_visual_qc(
        _pages(2), blueprint=_blueprint(2), make_doc=lambda pg: pg.html,
        regen_page=lambda i, p, pr: None, gate_enabled=False,
    )
    assert summary["overflow"]["skipped"] == "OVERFLOW_GATE_ENABLED=false"
    assert summary["overflow"]["checked_pages"] == []
    assert summary["checked_pages"] == [1, 2] and summary["issue_pages"] == []  # VL 只补拍一次


# ---- 任务D：元素级检测（组件内裁剪 + 兄弟重叠）----


def _clip(desc="词汇卡 第2张/共4张（spread…）", px=30):
    return {"over": 0, "clips": [{"desc": desc, "px": px}], "overlaps": []}


def test_element_clip_triggers_regen_with_component_feedback(monkeypatch):
    monkeypatch.setattr("app.core.config.settings.VISION_API_KEY", "")
    seq = [([b"a"], [_clip()], None), ([b"a1"], [{"over": 0, "clips": [], "overlaps": []}], None)]
    monkeypatch.setattr(vqc, "_screenshot_pages", lambda docs, deadline: seq.pop(0))
    regen_calls: list = []

    def regen(i, pg, problems):
        regen_calls.append(problems)
        return _ContentPage(title=pg.title, intent="i", html='<div class="page-focus"><p>slim</p></div>')

    out, summary = vqc.run_visual_qc(
        _pages(1), blueprint=_blueprint(1), make_doc=lambda pg: pg.html, regen_page=regen
    )
    of = summary["overflow"]
    assert len(regen_calls) == 1 and "词汇卡 第2张/共4张" in regen_calls[0][0] and "30px" in regen_calls[0][0]
    assert "精简该组件" in regen_calls[0][0]
    assert of["overflow_pages"] == {} and of["regenerated"] == {"1": 1}  # 页级无溢出，元素级单独触发
    assert of["still_element_issues"] == {} and of["still_overflowing"] == {}  # 修好即清零


def test_element_overlap_triggers_regen_with_pair_feedback(monkeypatch):
    monkeypatch.setattr("app.core.config.settings.VISION_API_KEY", "")
    bad = {"over": 0, "clips": [], "overlaps": [{"a": "时间线", "b": "计时器", "pct": 12}]}
    seq = [([b"a"], [bad], None), ([b"a1"], [{"over": 0, "clips": [], "overlaps": []}], None)]
    monkeypatch.setattr(vqc, "_screenshot_pages", lambda docs, deadline: seq.pop(0))
    regen_calls: list = []

    def regen(i, pg, problems):
        regen_calls.append(problems)
        return _ContentPage(title=pg.title, intent="i", html="<p>ok</p>")

    vqc.run_visual_qc(_pages(1), blueprint=_blueprint(1), make_doc=lambda pg: pg.html, regen_page=regen)
    assert "时间线" in regen_calls[0][0] and "计时器" in regen_calls[0][0] and "12%" in regen_calls[0][0]
    assert "互相遮挡" in regen_calls[0][0]


def test_element_issue_persists_caps_at_two_rounds_and_records(monkeypatch):
    monkeypatch.setattr("app.core.config.settings.VISION_API_KEY", "")
    monkeypatch.setattr(vqc, "_screenshot_pages", lambda docs, deadline: ([b"a"], [_clip(px=50)], None))
    regen_calls: list = []

    def regen(i, pg, problems):
        regen_calls.append(problems)
        return _ContentPage(title=pg.title, intent="i", html="<p>still bad</p>")

    out, summary = vqc.run_visual_qc(
        _pages(1), blueprint=_blueprint(1), make_doc=lambda pg: pg.html, regen_page=regen
    )
    of = summary["overflow"]
    assert len(regen_calls) == 2 and of["regenerated"] == {"1": 2}
    assert of["still_element_issues"] == {"1": [regen_calls[1][0]]}  # 仍违规保留并记录
    assert of["still_overflowing"] == {}  # 页级没超，不重复提示
    assert "still bad" in out[0].html


def test_element_issue_and_page_overflow_feed_regen_together(monkeypatch):
    monkeypatch.setattr("app.core.config.settings.VISION_API_KEY", "")
    both = {"over": 200, "clips": [{"desc": "原文段落卡（Para.2…）", "px": 45}], "overlaps": []}
    seq = [([b"a"], [both], None), ([b"a1"], [{"over": 5, "clips": [], "overlaps": []}], None)]
    monkeypatch.setattr(vqc, "_screenshot_pages", lambda docs, deadline: seq.pop(0))
    regen_calls: list = []

    def regen(i, pg, problems):
        regen_calls.append(problems)
        return _ContentPage(title=pg.title, intent="i", html="<p>ok</p>")

    vqc.run_visual_qc(_pages(1), blueprint=_blueprint(1), make_doc=lambda pg: pg.html, regen_page=regen)
    assert len(regen_calls[0]) == 2  # 页级问题 + 元素级问题一起带给重生成
    assert "内容超页约" in regen_calls[0][0] and "原文段落卡" in regen_calls[0][1]


def test_real_chromium_measures_clip_and_overlap_in_page():
    """真实 chromium 三级测量：line-clamp 裁剪与兄弟负 margin 叠压都能量出；干净页零违规"""
    pytest.importorskip("playwright")
    skeleton = _load_skeleton()
    clipped = (
        '<section class="page active"><div class="page-focus">'
        '<p style="height:40px;overflow:hidden">' + "line<br>" * 20 + "</p></div></section>"
    )
    overlapped = (
        '<section class="page active"><div class="page-focus">'
        '<p style="height:60px">aaa</p><p style="height:60px;margin-top:-40px">bbb</p></div></section>'
    )
    clean = '<section class="page active"><div class="page-focus"><p>ok</p></div></section>'
    docs = [
        skeleton.replace("</body>", clipped + "</body>"),
        skeleton.replace("</body>", overlapped + "</body>"),
        skeleton.replace("</body>", clean + "</body>"),
    ]
    import time as _t

    shots, overflows, err = vqc._screenshot_pages_real(docs, _t.time() + 60)
    assert err is None
    assert overflows[0]["clips"] and overflows[0]["clips"][0]["px"] > vqc.ELEMENT_CLIP_PX_THRESHOLD
    assert overflows[1]["overlaps"] and overflows[1]["overlaps"][0]["pct"] > 5
    assert overflows[2] == {"over": 0, "clips": [], "overlaps": []}


# ---- 相 B：VL 视觉检查 ----


def test_no_vision_key_skips_vl_only(monkeypatch):
    monkeypatch.setattr("app.core.config.settings.VISION_API_KEY", "")
    monkeypatch.setattr(vqc, "_screenshot_pages", lambda docs, deadline: ([b"s1", b"s2", b"s3"], [0, 0, 0], None))
    pages = _pages()
    out, summary = vqc.run_visual_qc(
        pages, blueprint=_blueprint(), make_doc=lambda pg: pg.html, regen_page=lambda i, p, pr: None
    )
    assert "未配置 VISION_API_KEY" in summary["skipped"]
    assert summary["overflow"]["checked_pages"] == [1, 2, 3]
    assert out == pages and summary["issue_pages"] == []


def test_vl_disabled_by_switch_runs_gate_only(monkeypatch):
    _with_key(monkeypatch)
    monkeypatch.setattr(vqc, "_screenshot_pages", lambda docs, deadline: ([b"s1"], [0], None))
    vl_called: list = []
    monkeypatch.setattr(vqc, "_vl_check", lambda shot, prompt: vl_called.append(1) or [])
    out, summary = vqc.run_visual_qc(
        _pages(1), blueprint=_blueprint(1), make_doc=lambda pg: pg.html, regen_page=lambda i, p, pr: None,
        vl_enabled=False,
    )
    assert vl_called == [] and "VISUAL_QC_ENABLED=false" in summary["skipped"]
    assert summary["overflow"]["checked_pages"] == [1]


def test_issue_page_regenerated_once(monkeypatch):
    _with_key(monkeypatch)
    monkeypatch.setattr(vqc, "_screenshot_pages", lambda docs, deadline: ([b"s1", b"s2", b"s3"], [0, 0, 0], None))
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
    monkeypatch.setattr(vqc, "_screenshot_pages", lambda docs, deadline: ([b"s1", b"s2"], [0, 0], None))
    monkeypatch.setattr(vqc, "_vl_check", lambda shot, prompt: None)
    pages = _pages(2)
    out, summary = vqc.run_visual_qc(
        pages, blueprint=_blueprint(2), make_doc=lambda pg: pg.html, regen_page=lambda i, p, pr: None
    )
    assert summary["unchecked_pages"] == [1, 2] and summary["checked_pages"] == []
    assert summary["issue_pages"] == [] and out == pages


def test_deadline_breach_skips_vl_regen(monkeypatch):
    _with_key(monkeypatch)
    monkeypatch.setattr(vqc, "_screenshot_pages", lambda docs, deadline: ([b"s1"], [0], None))
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
    monkeypatch.setattr(vqc, "_screenshot_pages", lambda docs, deadline: ([], [], "chromium 不可用"))
    pages = _pages(2)
    out, summary = vqc.run_visual_qc(
        pages, blueprint=_blueprint(2), make_doc=lambda pg: pg.html, regen_page=lambda i, p, pr: None
    )
    assert summary["error"] == "chromium 不可用"
    assert summary["overflow"]["skipped"] == "chromium 不可用"
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
    monkeypatch.setattr(vqc, "_screenshot_pages", lambda docs, deadline: ([b"s1"], [0], None))
    monkeypatch.setattr(vqc, "_vl_check", lambda shot, prompt: ["元素重叠"])

    def bad_regen(i, pg, problems):
        raise RuntimeError("rewrite failed")

    pages = _pages(1)
    out, summary = vqc.run_visual_qc(pages, blueprint=_blueprint(1), make_doc=lambda pg: pg.html, regen_page=bad_regen)
    assert out == pages and summary["issue_pages"] == [1] and summary["regenerated_pages"] == []


# ---- 骨架 CSS 溢出韧性契约 ----


def test_skeleton_overflow_resilience_contracts():
    css = _load_skeleton()
    assert "justify-content:safe center" in css  # 超页时顶端对齐，不上下双向裁剪
    assert "grid-template-columns:repeat(4,196px)" in css  # vocab 网格固定行列防叠压
    # 任务D 废固定高：卡片随内容等高伸展（minmax 行高 + min-height 卡 + 背面流内撑高），
    # 不再用固定 128px / line-clamp 截断（那是「叠压变裁剪」的总根源）
    assert "grid-auto-rows:minmax(128px,auto)" in css
    assert ".vocab-card{width:196px;min-height:128px;" in css
    assert "grid-auto-rows:128px" not in css and ";height:128px" not in css
    assert "-webkit-line-clamp" not in css
    assert ".vocab-card .back{min-height:128px;display:flex" in css  # 背面流内撑高，正面 absolute 跟随


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


def _page_reply(marker="body"):
    return (
        "```html\n<!--page: 1 | P-->\n<!--intent: i-->\n<div class=\"page-focus\"><p>"
        + marker + " word " * 30 + "</p></div>\n```\n"
    )


def _run_generate():
    return generate_html_courseware(
        title="测试课件",
        plan={"activity_designs": [], "objectives": [{"text": "read"}]},
        analysis={},
        text="A" * 200,
    )


def test_generate_visual_qc_end_to_end_all_clean(fake_llm, monkeypatch):
    _with_key(monkeypatch)
    monkeypatch.setattr(vqc, "_screenshot_pages", lambda docs, deadline: ([b"shot"] * 4, [0] * 4, None))
    monkeypatch.setattr(vqc, "_vl_check", lambda shot, prompt: [])
    fake_llm(_planner_json(), *[_page_reply() for _ in range(4)], *[_review_reply() for _ in range(4)])
    result = _run_generate()
    assert result.fallback is False
    qc = result.self_check["visual_qc"]
    assert qc["enabled"] is True and qc["checked_pages"] == [1, 2, 3, 4]
    assert qc["issue_pages"] == [] and qc["regenerated_pages"] == []
    assert qc["overflow"]["checked_pages"] == [1, 2, 3, 4]


def test_generate_visual_qc_disabled(fake_llm, monkeypatch):
    monkeypatch.setattr("app.core.config.settings.VISUAL_QC_ENABLED", False)
    monkeypatch.setattr("app.core.config.settings.OVERFLOW_GATE_ENABLED", False)
    fake_llm(_planner_json(), *[_page_reply() for _ in range(4)], *[_review_reply() for _ in range(4)])
    result = _run_generate()
    assert result.self_check["visual_qc"] == {"enabled": False}


def test_generate_gate_only_overflow_regenerated(fake_llm, monkeypatch):
    """VL 开关关闭 + 无 Key：溢出硬关卡照常执行并精简重生成超页页"""
    # 相位隔离：本测试校验溢出硬关卡，关闭交互自检避免其补强重生成错位消耗预排回复
    monkeypatch.setattr("app.core.config.settings.INTERACTION_CHECK_ENABLED", False)
    monkeypatch.setattr("app.core.config.settings.VISUAL_QC_ENABLED", False)
    monkeypatch.setattr("app.core.config.settings.VISION_API_KEY", "")
    seq = [([b"s"] * 4, [0, 300, 0, 0], None), ([b"s2new"], [0], None)]
    monkeypatch.setattr(vqc, "_screenshot_pages", lambda docs, deadline: seq.pop(0))
    fixed = _page_reply("REWRITTEN")
    fake_llm(_planner_json(), *[_page_reply() for _ in range(4)], *[_review_reply() for _ in range(4)], fixed)
    result = _run_generate()
    assert result.fallback is False
    qc = result.self_check["visual_qc"]
    of = qc["overflow"]
    assert "VISUAL_QC_ENABLED=false" in qc["skipped"]
    assert of["overflow_pages"] == {"2": 42} and of["regenerated"] == {"2": 1}
    assert of["still_overflowing"] == {} and "REWRITTEN" in result.html


def test_generate_visual_qc_issue_page_regenerated(fake_llm, monkeypatch):
    # 相位隔离：本测试校验 VL 问题页重生成，关闭交互自检避免其补强重生成错位消耗预排回复
    monkeypatch.setattr("app.core.config.settings.INTERACTION_CHECK_ENABLED", False)
    _with_key(monkeypatch)
    fixed_body = "```html\n<!--page: 1 | P-->\n<!--intent: i-->\n<div class=\"page-focus\"><p>REWRITTEN " + "visual fix " * 15 + "</p></div>\n```\n"
    monkeypatch.setattr(vqc, "_screenshot_pages", lambda docs, deadline: ([b"shot"] * 4, [0] * 4, None))
    monkeypatch.setattr(vqc, "_vl_check", lambda shot, prompt: (["文字溢出"] if ("精讲" in prompt or "总结" in prompt) else []))
    # VL 视问题页：精讲/总结页报问题 → 重生成回复接在评审回复之后
    fake_llm(
        _planner_json(),
        *[_page_reply() for _ in range(4)],
        *[_review_reply() for _ in range(4)],
        fixed_body,
        fixed_body,
    )
    result = _run_generate()
    assert result.fallback is False
    qc = result.self_check["visual_qc"]
    assert qc["issue_pages"] and qc["regenerated_pages"] == qc["issue_pages"]
    assert "REWRITTEN" in result.html
