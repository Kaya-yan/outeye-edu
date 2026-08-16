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
