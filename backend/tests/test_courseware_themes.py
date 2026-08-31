"""④b 主题库与风格规划测试：对比度契约 / token 注入拼装 / 冷启动映射 / 简报端点与风格档案"""

import pytest
from sqlalchemy import select

from app.core.security import get_current_user
from app.main import app
from app.models.courseware import TeacherStyleEvent
from app.api.api_v1.endpoints import courseware as cw_api
from app.services.courseware_themes import (
    THEMES,
    cold_start_recommend,
    get_theme,
    theme_catalog,
    themes_digest_for_planner,
)
from app.services.courseware_llm_generator import (
    ACCENT_PALETTE,
    _assemble_skeleton,
    _ContentPage,
    contrast_ratio,
    generate_html_courseware,
)
from app.services.courseware_theme_planner import plan_theme_brief, style_history_digest


GOOD_BODY = (
    '<div class="kicker">STAGE 1 · READING · 15 MIN</div>'
    "<h2>Deep Reading</h2>"
    '<div class="page-focus"><p>We start with the longest sentence and see how it works.</p></div>'
)


# ---- 主题契约 ----


def test_all_themes_meet_wcag_aa_on_paper_and_card():
    """每套主题：ink/text/muted 对 paper，四色强调色对 paper 与 card，全部 ≥4.5:1"""
    for theme in THEMES.values():
        paper, card = theme.tokens["paper"], theme.tokens["card"]
        for key in ("ink", "text", "muted"):
            ratio = contrast_ratio(theme.tokens[key], paper)
            assert ratio >= 4.5, f"{theme.id}.{key} 对 paper 仅 {ratio:.2f}:1"
        for accent in ACCENT_PALETTE:
            assert contrast_ratio(accent, paper) >= 4.5, f"{theme.id} 强调色 {accent} 对 paper 不足 4.5:1"
            assert contrast_ratio(accent, card) >= 4.5, f"{theme.id} 强调色 {accent} 对 card 不足 4.5:1"


def test_get_theme_falls_back_to_default():
    assert get_theme("humanities").id == "humanities"
    assert get_theme("nonsense").id == "academic"
    assert get_theme(None).id == "academic"


def test_theme_catalog_and_digest_shapes():
    catalog = theme_catalog()
    assert [c["id"] for c in catalog] == ["academic", "humanities", "fresh"]
    for c in catalog:
        assert {"id", "name", "tagline", "description", "default_accent", "colors"} <= set(c)
        assert c["colors"]["paper"].startswith("#") and len(c["colors"]["paper"]) == 7
    digest = themes_digest_for_planner()
    assert "academic" in digest and "humanities" in digest and "fresh" in digest


def test_cold_start_recommend_by_course_type():
    assert cold_start_recommend("文学阅读") == "humanities"
    assert cold_start_recommend("视听说") == "fresh"
    assert cold_start_recommend("学术写作") == "academic"
    assert cold_start_recommend("离谱课型") == "academic"
    assert cold_start_recommend(None) == "academic"


# ---- 拼装注入 ----


def test_assemble_injects_theme_tokens_and_extra_css():
    pages = [_ContentPage(title="封面", intent="建立情境", html=GOOD_BODY)]
    html = _assemble_skeleton("测试", "#b5493e", pages, theme=get_theme("humanities"))
    assert "__TOKEN_BLOCK__" not in html and "__THEME_EXTRA__" not in html
    assert "--paper:#fbf6ed" in html and "--ink:#4e3527" in html
    assert "--accent:#b5493e" in html  # accent-soft 与主题纸色混合
    assert ".accent-rule{width:56px" in html  # 主题微调样式已注入


def test_assemble_default_theme_keeps_baseline_look():
    pages = [_ContentPage(title="封面", intent="i", html=GOOD_BODY)]
    html = _assemble_skeleton("测试", "#35507a", pages)
    assert "--paper:#faf9f5" in html and "--fs-body:21px" in html
    assert 'class="page"' in html


class _FakeRAG:
    use_api = True
    replies: list = []

    def __init__(self, **kwargs):
        pass

    def _generate_with_api(self, messages):
        reply = type(self).replies.pop(0) if type(self).replies else _deck_answer()
        return reply, {}


def _deck_answer(n_pages=5):
    interactions = [
        '<details class="reveal"><summary>Q1</summary><p>A1</p></details>',
        '<div class="vocab-grid"><div class="vocab-card"><div class="inner"><div class="front">word</div><div class="back">释义（第1段）</div></div></div></div>',
        '<ol class="timeline"><li>step one</li><li>step two</li></ol>',
    ]
    parts = ["ACCENT: #3e6b5a\n"]
    for i in range(n_pages):
        parts.append(
            f"```html\n<!--page: {i + 1} | Page {i + 1}-->\n<!--intent: 意图{i + 1}-->\n{GOOD_BODY + interactions[i % 3]}\n```\n"
        )
    parts.append('```json\n{"prompt_version": "v2", "pages_count": %d}\n```\n' % n_pages)
    return "\n".join(parts)


def _run_generate(theme=None):
    return generate_html_courseware(
        title="测试课件",
        plan={"activity_designs": [{"name": f"环节{i}", "duration": "10 分钟", "objective": "o", "steps": "s"} for i in range(1, 5)]},
        analysis={},
        text="A" * 200,
        theme=theme,
    )


@pytest.fixture()
def fake_llm(monkeypatch):
    def install(*replies: str):
        _FakeRAG.replies = list(replies)
        _FakeRAG.use_api = True
        monkeypatch.setattr("app.services.rag.RAGGenerator", _FakeRAG)

    return install


def test_generate_with_theme_applies_tokens(fake_llm):
    fake_llm(_deck_answer())
    result = _run_generate("humanities")
    assert result.fallback is False
    assert "--paper:#fbf6ed" in result.html
    assert result.self_check["theme"] == "humanities"
    assert result.editor_schema["meta"]["source_meta"]["theme"] == "humanities"


def test_generate_invalid_theme_falls_back_to_default(fake_llm):
    fake_llm(_deck_answer())
    result = _run_generate("retro")
    assert result.self_check["theme"] == "academic"


# ---- 风格规划 ----


@pytest.fixture()
def fake_planner_llm(monkeypatch):
    def install(*replies, use_api=True):
        _FakeRAG.replies = list(replies)
        _FakeRAG.use_api = use_api
        monkeypatch.setattr("app.services.rag.RAGGenerator", _FakeRAG)

    return install


BRIEF_ARGS = dict(title="T", text="word " * 100, course_type="文化阅读")


def test_planner_parses_llm_json(fake_planner_llm):
    fake_planner_llm('{"course_type": "文化阅读", "recommended_theme": "humanities", "reason": "散文叙事温润", "design_notes": "突出意象词卡"}')
    brief = plan_theme_brief(**BRIEF_ARGS)
    assert brief["source"] == "llm" and brief["recommended_theme"] == "humanities"
    assert "散文" in brief["reason"]


def test_planner_rejects_unknown_theme_then_cold_start(fake_planner_llm):
    fake_planner_llm('{"course_type": "x", "recommended_theme": "vaporwave", "reason": "r", "design_notes": "d"}')
    brief = plan_theme_brief(**BRIEF_ARGS)
    assert brief["source"] == "cold_start" and brief["recommended_theme"] == "humanities"


def test_planner_garbage_output_falls_back(fake_planner_llm):
    fake_planner_llm("我认为人文主题最好。")
    brief = plan_theme_brief(**BRIEF_ARGS)
    assert brief["source"] == "cold_start" and brief["recommended_theme"] == "humanities"


def test_planner_no_api_uses_cold_start(fake_planner_llm):
    fake_planner_llm(use_api=False)
    brief = plan_theme_brief(title="T", text="word " * 100, course_type="视听说")
    assert brief["source"] == "cold_start" and brief["recommended_theme"] == "fresh"


def test_style_history_digest():
    assert style_history_digest([]) == "（暂无记录）"
    class _E:
        def __init__(self, theme):
            self.theme = theme
    digest = style_history_digest([_E("academic"), _E("academic"), _E("fresh")])
    assert "学术讲义×2" in digest and "清新课堂×1" in digest and "近 3 次" in digest


# ---- 端点与风格档案 ----


def _auth_as(user_id):
    async def override():
        return {"user_id": user_id, "email": "t@example.com", "is_admin": False}

    app.dependency_overrides[get_current_user] = override


@pytest.mark.asyncio
async def test_theme_brief_endpoint_returns_catalog_and_records_event(test_db_session, client, monkeypatch):
    _auth_as("user-1")

    def fake_plan(**kwargs):
        return {"course_type": "文化阅读", "recommended_theme": "humanities", "reason": "r", "design_notes": "d", "source": "llm"}

    monkeypatch.setattr(cw_api, "plan_theme_brief", fake_plan)
    resp = client.post("/api/v1/courseware/theme-brief", json={
        "analysis_id": None, "title": "T", "text": "word " * 50, "course_type": "文化阅读",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["recommended_theme"] == "humanities"
    assert [t["id"] for t in body["themes"]] == ["academic", "humanities", "fresh"]

    events = (await test_db_session.execute(select(TeacherStyleEvent))).scalars().all()
    assert len(events) == 1 and events[0].event_type == "recommended" and events[0].theme == "humanities"


@pytest.mark.asyncio
async def test_next_generate_event_type_chosen_then_regenerated(test_db_session):
    assert await cw_api._next_generate_event_type(test_db_session, "user-1", "ana-1") == "chosen"
    await cw_api._record_style_event(
        test_db_session, user_id="user-1", analysis_id="ana-1", event_type="chosen", theme="academic"
    )
    assert await cw_api._next_generate_event_type(test_db_session, "user-1", "ana-1") == "regenerated"
    # 其他教师 / 无 analysis_id 不受影响
    assert await cw_api._next_generate_event_type(test_db_session, "user-2", "ana-1") == "chosen"
    assert await cw_api._next_generate_event_type(test_db_session, "user-1", None) == "chosen"
