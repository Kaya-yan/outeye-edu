"""③ 历史恢复测试：plan-confirm 幂等 / resume-state 推导与降级 / 所有权 / 进度只进不退 / 列表 furthest_step"""

import pytest
from sqlalchemy import select

from app.core.security import get_current_user
from app.main import app
from app.models.analysis import AnalysisRecord, AnalysisProgress, LessonPlanVersion
from app.api.api_v1.endpoints.analysis_whitebox import _persist_plan_version


PLAN_RESULT = {
    "text_title": "测试课文",
    "teaching_plan": {"framework": "POA", "objectives": [{"text": "read"}]},
}


async def _seed_record(session, record_id="rec-1", user_id="user-1", analysis_status="completed"):
    record = AnalysisRecord(
        id=record_id,
        user_id=user_id,
        text_title="测试课文",
        text_content="word " * 30,
        analysis_status=analysis_status,
    )
    session.add(record)
    await session.commit()
    return record


def _auth_as(user_id):
    async def override():
        return {"user_id": user_id, "email": "t@example.com", "is_admin": False}

    app.dependency_overrides[get_current_user] = override


@pytest.mark.asyncio
async def test_plan_confirm_idempotent(test_db_session, client):
    """重复确认：同一行覆盖、同响应、进度到 confirmed"""
    await _seed_record(test_db_session)
    _auth_as("user-1")
    body = {"mode": "enhanced", "result": PLAN_RESULT}

    r1 = client.post("/api/v1/analysis/rec-1/plan-confirm", json=body)
    r2 = client.post("/api/v1/analysis/rec-1/plan-confirm", json=body)

    assert r1.status_code == 200 and r2.status_code == 200
    assert r1.json() == r2.json()
    rows = (await test_db_session.execute(select(LessonPlanVersion))).scalars().all()
    assert len(rows) == 1 and rows[0].mode == "confirmed"
    progress = (await test_db_session.execute(select(AnalysisProgress))).scalar_one()
    assert progress.furthest_step == "confirmed"
    assert progress.confirmed_plan_id == rows[0].id


@pytest.mark.asyncio
async def test_resume_state_derived_from_analysis_status(test_db_session, client):
    """无进度行时：completed → analysis，未完成 → input"""
    await _seed_record(test_db_session, record_id="rec-done", analysis_status="completed")
    await _seed_record(test_db_session, record_id="rec-pending", analysis_status="pending")
    _auth_as("user-1")

    done = client.get("/api/v1/analysis/rec-done/resume-state").json()
    pending = client.get("/api/v1/analysis/rec-pending/resume-state").json()

    assert done["furthest_step"] == "analysis"
    assert pending["furthest_step"] == "input"
    assert done["versions"] == {"basic": None, "enhanced": None}
    assert done["confirmed"] is None


@pytest.mark.asyncio
async def test_resume_endpoints_require_owner(test_db_session, client):
    await _seed_record(test_db_session, user_id="user-1")
    _auth_as("user-2")
    assert client.get("/api/v1/analysis/rec-1/resume-state").status_code == 404
    assert client.post(
        "/api/v1/analysis/rec-1/plan-confirm", json={"mode": "basic", "result": PLAN_RESULT}
    ).status_code == 404


@pytest.mark.asyncio
async def test_progress_forward_only_and_resume_payload(test_db_session, client):
    """确认后再生成版本：进度不回退；恢复载荷含双版本与确认快照"""
    await _seed_record(test_db_session)
    _auth_as("user-1")

    await _persist_plan_version(test_db_session, "rec-1", "user-1", "enhanced", PLAN_RESULT)
    client.post("/api/v1/analysis/rec-1/plan-confirm", json={"mode": "basic", "result": PLAN_RESULT})
    await _persist_plan_version(test_db_session, "rec-1", "user-1", "basic", PLAN_RESULT)

    state = client.get("/api/v1/analysis/rec-1/resume-state").json()
    assert state["furthest_step"] == "confirmed"
    assert state["versions"]["enhanced"]["teaching_plan"]["framework"] == "POA"
    assert state["versions"]["basic"] is not None
    assert state["confirmed"]["origin_mode"] == "basic"
    assert state["confirmed"]["result"]["text_title"] == "测试课文"


@pytest.mark.asyncio
async def test_resume_state_skips_corrupt_version_json(test_db_session, client):
    """版本 JSON 损坏时跳过该版本，不报错"""
    await _seed_record(test_db_session)
    test_db_session.add(LessonPlanVersion(
        analysis_id="rec-1", user_id="user-1", mode="basic", result_json="{not json"
    ))
    await test_db_session.commit()
    _auth_as("user-1")

    state = client.get("/api/v1/analysis/rec-1/resume-state").json()
    assert state["versions"]["basic"] is None
    assert state["furthest_step"] == "analysis"


@pytest.mark.asyncio
async def test_persist_version_skips_invalid_analysis(test_db_session, client):
    """非本人 / 不存在 / 缺省 analysis_id：静默跳过不落库"""
    await _seed_record(test_db_session, user_id="user-1")
    await _persist_plan_version(test_db_session, "rec-1", "user-2", "basic", PLAN_RESULT)
    await _persist_plan_version(test_db_session, "missing", "user-1", "basic", PLAN_RESULT)
    await _persist_plan_version(test_db_session, None, "user-1", "basic", PLAN_RESULT)

    rows = (await test_db_session.execute(select(LessonPlanVersion))).scalars().all()
    assert rows == []


@pytest.mark.asyncio
async def test_projects_list_includes_furthest_step(test_db_session, client):
    await _seed_record(test_db_session, record_id="rec-a")
    await _seed_record(test_db_session, record_id="rec-b", analysis_status="pending")
    _auth_as("user-1")

    client.post("/api/v1/analysis/rec-a/plan-confirm", json={"mode": "enhanced", "result": PLAN_RESULT})
    items = client.get("/api/v1/projects").json()

    by_id = {p["id"]: p for p in items}
    assert by_id["rec-a"]["furthest_step"] == "confirmed"
    assert by_id["rec-b"]["furthest_step"] is None
