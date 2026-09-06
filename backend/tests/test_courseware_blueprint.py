"""S4 蓝图可编辑测试：教师蓝图直通逐页生成 / 无效蓝图回退内部规划 / 蓝图规划端点 / 确认事件"""

import json
import time
from contextlib import asynccontextmanager

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from app.core.security import get_current_user
from app.main import app
from app.models.courseware import TeacherStyleEvent
from app.services.courseware_llm_generator import generate_html_courseware


# ---- 共享 fake LLM（与 test_courseware_two_stage 同模式） ----


class _FakeRAG:
    use_api = True
    replies: list = []

    def __init__(self, **kwargs):
        pass

    def _generate_with_api(self, messages):
        reply = type(self).replies.pop(0) if type(self).replies else _page_reply()
        return reply, {}


@pytest.fixture()
def fake_llm(monkeypatch):
    def install(*replies: str):
        _FakeRAG.replies = list(replies)
        _FakeRAG.use_api = True
        monkeypatch.setattr("app.services.rag.RAGGenerator", _FakeRAG)

    return install


def _planner_json(n_paras=2, accent="#35507a"):
    pages = [
        {"kind": "cover", "title": "", "intent": "建立情境", "para": None},
        {"kind": "vocab", "title": "词汇预教", "intent": "预教难点词", "para": None},
    ]
    pages += [{"kind": "deep_reading", "title": f"第{i}段精讲", "intent": f"细读第{i}段", "para": i} for i in range(1, n_paras + 1)]
    pages.append({"kind": "summary", "title": "总结", "intent": "回收", "para": None})
    return "```json\n" + json.dumps({"accent": accent, "pages": pages, "notes": "n"}, ensure_ascii=False) + "\n```"


def _page_reply(page_no=1, title="第1段精讲"):
    body = (
        '<div class="kicker">课文精讲 · 第 1 段</div>'
        "<h2>Deep Reading</h2>"
        '<div class="page-focus"><p>A solid page body with <mark class="kw">symbol</mark> inside.</p></div>'
    )
    return f"```html\n<!--page: {page_no} | {title}-->\n<!--intent: 细读第{page_no}段-->\n{body}\n```\n"


def _plan(n_activities: int = 4) -> dict:
    return {
        "activity_designs": [
            {"name": f"环节{i}", "duration": "10 分钟", "objective": "o", "steps": "s"}
            for i in range(1, n_activities + 1)
        ],
        "objectives": [{"text": "read"}],
    }


TEACHER_BLUEPRINT = [
    {"kind": "cover", "title": "封面", "intent": "建立情境", "para": None},
    {"kind": "deep_reading", "title": "第1段精讲", "intent": "细读第1段", "para": 1},
    {"kind": "summary", "title": "总结", "intent": "回收", "para": None},
]


def _generate(**kwargs):
    return generate_html_courseware(
        title="测试课件",
        plan=_plan(),
        analysis={},
        text="A" * 200,
        **kwargs,
    )


# ---- 服务层：教师蓝图 ----


def test_generate_with_teacher_blueprint_skips_planner(fake_llm):
    messages: list = []
    fake_llm(*[_page_reply() for _ in range(4)])
    result = _generate(blueprint=TEACHER_BLUEPRINT, accent="#b5493e", progress_cb=messages.append)
    assert result.fallback is False
    sc = result.self_check
    assert sc["blueprint"]["source"] == "teacher"
    assert sc["pages_count"] == 3
    assert sc["accent"] == "#b5493e"
    assert [p["kind"] for p in sc["blueprint"]["pages"]] == ["cover", "deep_reading", "summary"]
    assert any("已采用教师确认蓝图（3 页）" in m for m in messages)
    # 教师编辑后的蓝图原样落库，供 S4 编辑/回溯复用
    stored = result.editor_schema["meta"]["source_meta"]["page_blueprint"]
    assert [p["kind"] for p in stored] == ["cover", "deep_reading", "summary"]
    assert stored[0]["title"] == "封面"


def test_generate_invalid_teacher_blueprint_replans_internally(fake_llm):
    fake_llm(_planner_json(), *[_page_reply() for _ in range(5)])
    bad = [
        {"kind": "cover", "title": "c", "intent": "i", "para": None},
        {"kind": "summary", "title": "s", "intent": "i", "para": None},
    ]  # 无 deep_reading → 段落 1 未覆盖
    result = _generate(blueprint=bad)
    assert result.fallback is False
    assert result.self_check["blueprint"]["source"] == "llm"
    assert "教师蓝图未过校验" in (result.self_check["blueprint"]["note"] or "")


def test_generate_teacher_blueprint_bad_accent_uses_default(fake_llm):
    fake_llm(*[_page_reply() for _ in range(4)])
    result = _generate(blueprint=TEACHER_BLUEPRINT, accent="#ff0000")
    assert result.self_check["accent"] != "#ff0000"
    assert "不在色板" in (result.self_check["accent_note"] or "")


# ---- 端点层：蓝图规划 / 确认事件 ----


@asynccontextmanager
async def _noop_lifespan(app):
    yield


def _auth_as(user_id):
    async def override():
        return {"user_id": user_id, "email": "t@example.com", "is_admin": False}

    app.dependency_overrides[get_current_user] = override


_PLAN_PAYLOAD = {
    "title": "测试课件",
    "plan": {"activity_designs": [], "objectives": [{"text": "read"}]},
    "analysis": {},
    "text": "A" * 200,
    "language_name": "英语",
    "duration_minutes": 45,
    "course_type": "精读",
}


def _poll(c: TestClient, task_id: str, tries: int = 40) -> dict:
    st = {}
    for _ in range(tries):
        st = c.get(f"/api/v1/courseware/generate/{task_id}").json()
        if st["status"] in ("done", "error"):
            return st
        time.sleep(0.05)
    return st


def test_blueprint_endpoint_plans_pages(fake_llm, monkeypatch):
    fake_llm(_planner_json(n_paras=1))
    monkeypatch.setattr(app.router, "lifespan_context", _noop_lifespan)
    _auth_as("user-1")
    try:
        with TestClient(app) as c:
            r = c.post("/api/v1/courseware/blueprint", json=_PLAN_PAYLOAD)
            assert r.status_code == 202
            st = _poll(c, r.json()["task_id"])
            assert st["status"] == "done", st
            res = st["result"]
            assert res["source"] == "llm"
            assert res["n_paras"] == 1
            assert res["accent"] == "#35507a"
            kinds = [p["kind"] for p in res["blueprint"]]
            assert kinds[0] == "cover" and kinds[-1] == "summary" and "deep_reading" in kinds
            # 蓝图页带 title/intent/para，前端编辑器直接可用
            page = next(p for p in res["blueprint"] if p["kind"] == "deep_reading")
            assert page["para"] == [1] and page["title"] and page["intent"]
    finally:
        app.dependency_overrides.clear()


def test_blueprint_endpoint_llm_down_reports_error(fake_llm, monkeypatch):
    fake_llm()
    _FakeRAG.use_api = False
    monkeypatch.setattr(app.router, "lifespan_context", _noop_lifespan)
    _auth_as("user-1")
    try:
        with TestClient(app) as c:
            r = c.post("/api/v1/courseware/blueprint", json=_PLAN_PAYLOAD)
            st = _poll(c, r.json()["task_id"])
            assert st["status"] == "error"
            assert "LLM 不可用" in (st["error"] or "")
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_generate_with_blueprint_records_confirmed_event(fake_llm, test_engine, monkeypatch):
    from app.api.api_v1.endpoints import courseware as cw_module

    factory = sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)
    monkeypatch.setattr(cw_module, "AsyncSessionLocal", factory)
    fake_llm(*[_page_reply() for _ in range(4)])
    monkeypatch.setattr(app.router, "lifespan_context", _noop_lifespan)
    _auth_as("user-1")
    try:
        with TestClient(app) as c:
            r = c.post("/api/v1/courseware/generate", json={
                **_PLAN_PAYLOAD,
                "format": "html",
                "blueprint": TEACHER_BLUEPRINT,
                "blueprint_edits": {"count": 2},
                "accent": "#35507a",
            })
            assert r.status_code == 202
            st = _poll(c, r.json()["task_id"])
            assert st["status"] == "done", st
            assert st["project_id"]
        async with factory() as s:
            events = (await s.execute(select(TeacherStyleEvent))).scalars().all()
        types = [e.event_type for e in events]
        assert "chosen" in types and "blueprint_confirmed" in types
        ev = next(e for e in events if e.event_type == "blueprint_confirmed")
        assert ev.theme == "academic"
        assert ev.extra_json == {"source": "teacher_confirmed", "edits": {"count": 2}, "pages_final": 3}
    finally:
        app.dependency_overrides.clear()
