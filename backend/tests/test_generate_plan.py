"""
教案生成请求与模式测试（TDD）

目标：
1. GeneratePlanRequest 支持 duration_minutes + mode，含默认值与校验
2. mode="basic" 跳过证据标注，mode="enhanced" 含证据标注
"""

import pytest
from pydantic import ValidationError

from app.api.api_v1.endpoints.analysis_whitebox import GeneratePlanRequest


class TestGeneratePlanRequest:
    def test_defaults(self):
        req = GeneratePlanRequest(text="x" * 20)
        assert req.duration_minutes == 90
        assert req.mode == "enhanced"

    def test_accepts_custom(self):
        req = GeneratePlanRequest(text="x" * 20, duration_minutes=60, mode="basic")
        assert req.duration_minutes == 60
        assert req.mode == "basic"

    def test_validates_duration_range(self):
        with pytest.raises(ValidationError):
            GeneratePlanRequest(text="x" * 20, duration_minutes=0)
        with pytest.raises(ValidationError):
            GeneratePlanRequest(text="x" * 20, duration_minutes=200)

    def test_validates_mode(self):
        with pytest.raises(ValidationError):
            GeneratePlanRequest(text="x" * 20, mode="invalid")


class TestGeneratePlanMode:
    """生成模式测试（走 fallback 路径，避免真实 LLM 调用）"""

    def _make(self, monkeypatch, mode):
        from app.services.analysis.fusion_generator import generate_teaching_plan

        class FakeGenerator:
            use_api = False

        monkeypatch.setattr(
            "app.services.rag.RAGGenerator", lambda **kw: FakeGenerator()
        )

        analysis = {
            "learner_gap": {"student_level": "B1", "gap": "", "gap_description": ""}
        }
        return generate_teaching_plan(
            "t", "x" * 20, analysis, [], [], mode=mode
        )

    def test_basic_mode_skips_evidence(self, monkeypatch):
        plan = self._make(monkeypatch, "basic")
        assert plan.evidence_annotations == {}

    def test_enhanced_mode_has_evidence(self, monkeypatch):
        plan = self._make(monkeypatch, "enhanced")
        assert plan.evidence_annotations != {}


# ============ 异步链路（POST /generate-plan-async + GET /generation-tasks）测试 ============
# 覆盖 2026-10-25 前的空档：异步教案生成的任务契约。
# 隔离范式沿用 test_courseware_blueprint：noop lifespan + sqlite factory + with TestClient。

import time
from contextlib import asynccontextmanager

from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.main import app
from app.api.api_v1.endpoints import analysis_whitebox as wb_module


@asynccontextmanager
async def _noop_lifespan(app):
    yield


def _auth_as(user_id):
    async def override():
        return {"user_id": user_id, "email": "t@example.com", "is_admin": False}

    app.dependency_overrides[get_current_user] = override


class _FallbackGenerator:
    """use_api=False → fusion_generator 走确定性模板降级（生产 LLM 不可用时的真实路径）"""

    use_api = False

    def __init__(self, **kwargs):
        pass


class TestGeneratePlanAsyncEndpoint:
    TEXT = ("The little cat sat on the mat and looked at the red ball. "
            "She was happy because the sun was warm today.") * 2

    def test_async_flow_returns_202_then_polls_to_done(self, monkeypatch, test_engine):
        factory = sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)
        monkeypatch.setattr(wb_module, "AsyncSessionLocal", factory)
        monkeypatch.setattr("app.services.rag.RAGGenerator", lambda **kw: _FallbackGenerator())
        monkeypatch.setattr(app.router, "lifespan_context", _noop_lifespan)
        _auth_as("user-1")
        try:
            with TestClient(app) as c:
                r = c.post("/api/v1/analysis/generate-plan-async", json={
                    "text": self.TEXT, "duration_minutes": 45, "mode": "basic",
                })
                assert r.status_code == 202
                task_id = r.json()["task_id"]
                assert task_id

                st = {}
                for _ in range(60):  # 白盒确定性 + 模板降级，秒级完成
                    st = c.get(f"/api/v1/analysis/generation-tasks/{task_id}").json()
                    if st["status"] in ("done", "error"):
                        break
                    time.sleep(0.2)

                assert st["status"] == "done", st
                result = st["result"]
                assert result["fallback"] is True               # 模板降级路径
                assert result["model"] == "template-fallback"
                assert result["teaching_plan"]["activity_designs"]  # 教案主体存在
                assert result["generation_settings"]["duration_minutes"] == 45
                assert "total_duration" in result
        finally:
            app.dependency_overrides.clear()

    def test_generation_task_poll_contract_ownership_and_404(self, monkeypatch):
        """轮询契约：属主可见 / 他人 404 / 未知任务 404 / error 状态原样透出"""
        monkeypatch.setattr(app.router, "lifespan_context", _noop_lifespan)
        wb_module._PLAN_TASKS["task-mine"] = {
            "status": "done", "progress": "完成", "user_id": "user-1",
            "created_ts": time.time(), "result": {"teaching_plan": {"framework": "PWP"}},
        }
        wb_module._PLAN_TASKS["task-broken"] = {
            "status": "error", "progress": "", "user_id": "user-1",
            "created_ts": time.time(), "error": "教案生成失败，请稍后重试",
        }
        try:
            with TestClient(app) as c:
                _auth_as("user-1")
                ok = c.get("/api/v1/analysis/generation-tasks/task-mine")
                assert ok.status_code == 200
                assert ok.json()["result"]["teaching_plan"]["framework"] == "PWP"

                err = c.get("/api/v1/analysis/generation-tasks/task-broken")
                assert err.status_code == 200
                assert err.json()["status"] == "error"

                assert c.get("/api/v1/analysis/generation-tasks/task-nope").status_code == 404

                _auth_as("user-2")  # 非属主：等同不存在
                assert c.get("/api/v1/analysis/generation-tasks/task-mine").status_code == 404
        finally:
            wb_module._PLAN_TASKS.pop("task-mine", None)
            wb_module._PLAN_TASKS.pop("task-broken", None)
            app.dependency_overrides.clear()
