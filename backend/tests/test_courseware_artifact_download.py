"""下载产物端点回归：异步 session 上惰性访问 artifact.project 曾触发 MissingGreenlet 500"""

from uuid import uuid4

from urllib.parse import unquote

import pytest
from sqlalchemy import select

from app.core.security import get_current_user
from app.main import app
from app.models.courseware import CoursewareProject, ExportArtifact, TeacherStyleEvent


def _auth_as(user_id):
    async def override():
        return {"user_id": user_id, "email": "t@example.com", "is_admin": False}

    app.dependency_overrides[get_current_user] = override


@pytest.mark.asyncio
async def test_download_artifact_reads_project_meta_without_lazy_load(
    test_db_session, client, monkeypatch, tmp_path
):
    monkeypatch.setattr("app.core.config.settings.UPLOAD_DIR", str(tmp_path))
    artifacts_dir = tmp_path / "artifacts"
    artifacts_dir.mkdir()
    (artifacts_dir / "courseware.pptx").write_bytes(b"PK\x03\x04fake-pptx")

    project_id = str(uuid4())
    artifact_id = str(uuid4())
    test_db_session.add_all([
        CoursewareProject(
            id=project_id,
            owner_user_id="user-1",
            title="标题",
            source_meta={"theme": "academic"},
        ),
        ExportArtifact(
            id=artifact_id,
            project_id=project_id,
            format="pptx",
            file_name="课件导出.pptx",
            storage_path="artifacts/courseware.pptx",
        ),
    ])
    await test_db_session.commit()

    _auth_as("user-1")
    resp = client.get(f"/api/v1/courseware/artifacts/{artifact_id}/download")

    assert resp.status_code == 200
    assert resp.content == b"PK\x03\x04fake-pptx"
    assert resp.headers["content-type"] == (
        "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    )
    disposition = resp.headers.get("content-disposition", "")
    assert "attachment" in disposition
    assert unquote(disposition).endswith("课件导出.pptx")

    # source_meta.theme 命中 _record_style_event（原崩溃点所在分支），事件确实落库
    events = (await test_db_session.execute(select(TeacherStyleEvent))).scalars().all()
    assert any(
        e.event_type == "exported" and e.theme == "academic"
        and e.extra_json.get("artifact_id") == artifact_id
        for e in events
    )


@pytest.mark.asyncio
async def test_download_artifact_rejects_other_owner(test_db_session, client, monkeypatch, tmp_path):
    monkeypatch.setattr("app.core.config.settings.UPLOAD_DIR", str(tmp_path))
    project_id = str(uuid4())
    artifact_id = str(uuid4())
    test_db_session.add_all([
        CoursewareProject(id=project_id, owner_user_id="user-1", title="T"),
        ExportArtifact(id=artifact_id, project_id=project_id, format="pptx",
                       file_name="a.pptx", storage_path="artifacts/a.pptx"),
    ])
    await test_db_session.commit()

    _auth_as("user-2")
    resp = client.get(f"/api/v1/courseware/artifacts/{artifact_id}/download")
    assert resp.status_code == 404
