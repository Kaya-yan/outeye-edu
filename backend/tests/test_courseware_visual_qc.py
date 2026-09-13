"""S6 视觉质检测试（两相）：遮挡硬关卡（geo-v3 元素级几何检测/两轮重生成/仍违规保留）+ VL 问题节
重生成 / 未配 key、超时、chromium 缺失降级 / 双开关独立门控 / 滚动骨架 CSS 契约 / 端到端接入"""

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


_CLEAN_M = {"clips": [], "overlaps": []}


def _clip(desc="词汇卡 第2张/共4张（spread…）", px=30):
    return {"clips": [{"desc": desc, "px": px}], "overlaps": []}


# ---- 相 A：遮挡硬关卡（geo-v3 元素级）----


def test_gate_two_rounds_then_keeps_and_records(monkeypatch):
    monkeypatch.setattr("app.core.config.settings.VISION_API_KEY", "")
    seq = [
        ([b"a", b"b", b"c"], [_clip(px=30), _CLEAN_M, _CLEAN_M], None),
        ([b"a1"], [_clip(px=20)], None),
        ([b"a2"], [_clip(px=15)], None),
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
    assert calls == [3, 1, 1]  # 全量测一次 + 单节复测两次
    assert of["gate_version"] == "geo-v3"
    assert of["regenerated"] == {"1": 2}
    assert "15px" in of["still_element_issues"]["1"][0]  # 两轮后仍违规：记录最后一轮复测出的问题
    assert "词汇卡" in regen_calls[0][1][0] and "30px" in regen_calls[0][1][0]
    assert "精简该组件" in regen_calls[0][1][0]
    assert "slim" in out[0].html and "page 2" in out[1].html  # 两轮精简稿被保留
    assert any("遮挡检测" in m and "第 1 节" in m for m in messages)
    assert "未配置 VISION_API_KEY" in summary["skipped"]  # 无 key 不影响硬关卡执行


def test_gate_fixed_in_one_round(monkeypatch):
    monkeypatch.setattr("app.core.config.settings.VISION_API_KEY", "")
    seq = [([b"a", b"b"], [_clip(px=25), _CLEAN_M], None), ([b"a1"], [_CLEAN_M], None)]
    monkeypatch.setattr(vqc, "_screenshot_pages", lambda docs, deadline: seq.pop(0))
    out, summary = vqc.run_visual_qc(
        _pages(2), blueprint=_blueprint(2), make_doc=lambda pg: pg.html,
        regen_page=lambda i, pg, pr: _ContentPage(title=pg.title, intent="i", html='<div class="page-focus"><p>ok</p></div>'),
    )
    of = summary["overflow"]
    assert of["regenerated"] == {"1": 1}
    assert of["still_element_issues"] == {} and "ok" in out[0].html


def test_gate_regen_none_keeps_original_and_records(monkeypatch):
    monkeypatch.setattr("app.core.config.settings.VISION_API_KEY", "")
    monkeypatch.setattr(vqc, "_screenshot_pages", lambda docs, deadline: ([b"a"], [_clip(px=40)], None))
    pages = _pages(1)
    out, summary = vqc.run_visual_qc(
        pages, blueprint=_blueprint(1), make_doc=lambda pg: pg.html, regen_page=lambda i, p, pr: None
    )
    of = summary["overflow"]
    assert out == pages and of["still_element_issues"]["1"] and of["regenerated"] == {"1": 1}


def test_gate_respects_deadline_no_regen(monkeypatch):
    monkeypatch.setattr("app.core.config.settings.VISION_API_KEY", "")
    monkeypatch.setattr(vqc, "_screenshot_pages", lambda docs, deadline: ([b"a"], [_clip(px=40)], None))
    pages = _pages(1)
    out, summary = vqc.run_visual_qc(
        pages, blueprint=_blueprint(1), make_doc=lambda pg: pg.html,
        regen_page=lambda i, p, pr: (_ for _ in ()).throw(AssertionError("超时后不应重生成")),
        budget_seconds=0.0,
    )
    assert out == pages
    assert summary["overflow"]["checked_pages"] == [1]
    assert summary["overflow"]["regenerated"] == {} and summary["overflow"]["still_element_issues"]["1"]


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


# ---- 任务D：元素级检测（组件内裁剪 + 全树兄弟重叠）----


def test_element_clip_triggers_regen_with_component_feedback(monkeypatch):
    monkeypatch.setattr("app.core.config.settings.VISION_API_KEY", "")
    seq = [([b"a"], [_clip()], None), ([b"a1"], [_CLEAN_M], None)]
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
    assert of["regenerated"] == {"1": 1}
    assert of["still_element_issues"] == {}  # 修好即清零


def test_element_overlap_triggers_regen_with_pair_feedback(monkeypatch):
    monkeypatch.setattr("app.core.config.settings.VISION_API_KEY", "")
    bad = {"clips": [], "overlaps": [{"a": "时间线", "b": "计时器", "pct": 12}]}
    seq = [([b"a"], [bad], None), ([b"a1"], [_CLEAN_M], None)]
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
    assert "still bad" in out[0].html


def test_element_clip_and_overlap_feed_regen_together(monkeypatch):
    monkeypatch.setattr("app.core.config.settings.VISION_API_KEY", "")
    both = {"clips": [{"desc": "原文段落卡（Para.2…）", "px": 45}], "overlaps": [{"a": "时间线", "b": "计时器", "pct": 30}]}
    seq = [([b"a"], [both], None), ([b"a1"], [_CLEAN_M], None)]
    monkeypatch.setattr(vqc, "_screenshot_pages", lambda docs, deadline: seq.pop(0))
    regen_calls: list = []

    def regen(i, pg, problems):
        regen_calls.append(problems)
        return _ContentPage(title=pg.title, intent="i", html="<p>ok</p>")

    vqc.run_visual_qc(_pages(1), blueprint=_blueprint(1), make_doc=lambda pg: pg.html, regen_page=regen)
    assert len(regen_calls[0]) == 2  # 裁剪 + 叠压一起带给重生成
    assert "原文段落卡" in regen_calls[0][0] and "时间线" in regen_calls[0][1]


def test_real_chromium_measures_clip_and_overlap_in_section():
    """真实 chromium geo-v3 测量：overflow:hidden 裁剪与兄弟负 margin 叠压都能量出；干净节零违规"""
    pytest.importorskip("playwright")
    skeleton = _load_skeleton()
    clipped = (
        '<section class="oe-section"><div class="page-focus">'
        '<p style="height:40px;overflow:hidden">' + "line<br>" * 20 + "</p></div></section>"
    )
    overlapped = (
        '<section class="oe-section"><div class="page-focus">'
        '<p style="height:60px">aaa</p><p style="height:60px;margin-top:-40px">bbb</p></div></section>'
    )
    clean = '<section class="oe-section"><div class="page-focus"><p>ok</p></div></section>'
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
    assert overflows[2] == {"clips": [], "overlaps": []}


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


# ---- 滚动骨架 CSS 契约 ----


def test_skeleton_scroll_contracts():
    css = _load_skeleton()
    # 版心：居中 min(820px, 100% - 3rem)，无固定高度、无 overflow:hidden 裁内容
    assert "#oe-content{width:min(820px,100% - 3rem);margin:0 auto;padding:52px 0 32px}" in css
    assert ".oe-section{margin:0 0 52px}" in css
    assert ".oe-chapter{margin:0 0 64px;scroll-margin-top:20px}" in css
    # 导航三件套：顶部进度条 / 固定章目录 / 返回顶部
    assert "#oe-progress" in css and "#oe-toc" in css and "#oe-backtop" in css
    assert "scrollIntoView({ behavior: 'smooth'" in css  # 目录平滑滚动
    assert "ArrowRight" in css and "ArrowLeft" in css  # ←/→ 切章键盘导航
    # 节淡入动效可全局关闭（reduced-motion / oe-no-anim 截图态 / oe-edit-all 编辑态）
    assert "body:not(.oe-no-anim):not(.oe-edit-all) .oe-section{opacity:0" in css
    assert "prefers-reduced-motion" in css and "IntersectionObserver" in css
    assert "-webkit-line-clamp" not in css  # 滚动版无固定高，无需截断（截断即裁内容违规源）


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


def test_generate_gate_only_element_issue_regenerated(fake_llm, monkeypatch):
    """VL 开关关闭 + 无 Key：遮挡硬关卡照常执行并精简重生成违规节"""
    # 相位隔离：本测试校验遮挡硬关卡，关闭交互自检避免其补强重生成错位消耗预排回复
    monkeypatch.setattr("app.core.config.settings.INTERACTION_CHECK_ENABLED", False)
    monkeypatch.setattr("app.core.config.settings.VISUAL_QC_ENABLED", False)
    monkeypatch.setattr("app.core.config.settings.VISION_API_KEY", "")
    seq = [([b"s"] * 4, [_CLEAN_M, _clip(px=30), _CLEAN_M, _CLEAN_M], None), ([b"s2new"], [_CLEAN_M], None)]
    monkeypatch.setattr(vqc, "_screenshot_pages", lambda docs, deadline: seq.pop(0))
    fixed = _page_reply("REWRITTEN")
    fake_llm(_planner_json(), *[_page_reply() for _ in range(4)], *[_review_reply() for _ in range(4)], fixed)
    result = _run_generate()
    assert result.fallback is False
    qc = result.self_check["visual_qc"]
    of = qc["overflow"]
    assert "VISUAL_QC_ENABLED=false" in qc["skipped"]
    assert of["regenerated"] == {"2": 1} and of["still_element_issues"] == {}
    assert "REWRITTEN" in result.html


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
