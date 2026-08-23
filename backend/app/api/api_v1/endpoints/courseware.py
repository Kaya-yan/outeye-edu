"""
教学课件工作台 API
"""

import asyncio
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Literal
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal, get_async_db
from app.core.security import get_current_user
from app.models.courseware import (
    ComponentDefinition,
    CoursewareProject,
    CoursewareVersion,
    PresentationProfile,
)
from app.services.courseware_bootstrap import (
    build_blank_courseware,
    build_courseware_from_plan,
    build_default_presentation_settings,
    build_imported_courseware,
)

router = APIRouter()


class CoursewareProjectCreate(BaseModel):
    title: str = Field(..., max_length=200)
    source_type: Literal["blank_template", "imported_html"] = "blank_template"
    source_plan_id: Optional[str] = None
    mode: Literal["slides", "longform"] = "slides"
    template_id: str = "classroom_default"
    source_meta: Optional[Dict[str, Any]] = None
    imported_html: Optional[str] = Field(None, max_length=5_000_000)


class CoursewareFromPlanCreate(BaseModel):
    title: str = Field(..., max_length=200)
    source_plan_id: Optional[str] = None
    mode: Literal["slides", "longform"] = "slides"
    template_id: str = "classroom_default"
    plan: Dict[str, Any]
    learner_gap: Optional[Dict[str, Any]] = None
    enhancement_tags: Optional[List[str]] = None
    source_meta: Optional[Dict[str, Any]] = None


class CoursewareGenerateRequest(BaseModel):
    """LLM 生成课件（HTML 链路）请求"""
    title: str = Field(..., max_length=200)
    plan: Dict[str, Any]
    analysis: Optional[Dict[str, Any]] = None      # 白盒分析子集（vocabulary/syntax/discourse）
    text: str = Field(..., min_length=10)           # 课文全文
    language_name: str = "英语"
    text_level: Optional[str] = None
    student_level: Optional[str] = None
    duration_minutes: int = Field(90, ge=5, le=180)
    course_type: Optional[str] = None
    class_size: Optional[int] = None
    native_language: Optional[str] = None
    learner_gap: Optional[Dict[str, Any]] = None
    enhancement_tags: Optional[List[str]] = None


# 课件生成任务注册表（进程内；重启丢失，前端轮询 404 时提示重试）
_GENERATION_TASKS: Dict[str, Dict[str, Any]] = {}
_TASK_TTL_SECONDS = 3600


def _prune_generation_tasks() -> None:
    now = time.time()
    stale = [tid for tid, s in _GENERATION_TASKS.items() if now - s.get("created_ts", now) > _TASK_TTL_SECONDS]
    for tid in stale:
        _GENERATION_TASKS.pop(tid, None)


async def _run_html_generation(task_id: str, payload: CoursewareGenerateRequest, current_user: dict) -> None:
    state = _GENERATION_TASKS[task_id]
    try:
        state.update(status="generating", progress="AI 正在设计课件页面…（约 1-2 分钟）")

        from app.services.courseware_llm_generator import generate_html_courseware

        async with AsyncSessionLocal() as db:
            comps = (
                await db.execute(select(ComponentDefinition).where(ComponentDefinition.scope == "official"))
            ).scalars().all()
            components = [c.to_dict() for c in comps]

        result = await asyncio.to_thread(
            generate_html_courseware,
            title=payload.title,
            plan=payload.plan,
            analysis=payload.analysis or {},
            text=payload.text,
            language_name=payload.language_name,
            text_level=payload.text_level or "",
            student_level=payload.student_level or "",
            duration_minutes=payload.duration_minutes,
            course_type=payload.course_type,
            class_size=payload.class_size,
            native_language=payload.native_language,
            components=components,
            learner_gap=payload.learner_gap,
            enhancement_tags=payload.enhancement_tags,
        )

        state.update(status="saving", progress="正在保存课件项目…")

        source_meta = dict(result.editor_schema.get("meta", {}).get("source_meta", {}))
        async with AsyncSessionLocal() as db:
            created = await _create_initial_project_state(
                title=payload.title,
                source_type="from_plan_llm",
                source_plan_id=None,
                mode="slides",
                template_id="classroom_default",
                source_meta=source_meta,
                current_user=current_user,
                db=db,
                bootstrap_payload={
                    "editor_schema_json": result.editor_schema,
                    "rendered_html": result.html,
                    "asset_manifest_json": {"items": [], "count": 0},
                    "structure_sync_json": result.structure_sync,
                },
            )
            try:
                from app.models.generation import GenerationLog

                db.add(GenerationLog(
                    user_id=current_user["user_id"],
                    analysis_id=None,
                    stage="courseware_html",
                    prompt_name="courseware_html_v1",
                    prompt_version=result.prompt_version,
                    model=result.model,
                    fallback="yes" if result.fallback else "no",
                    generation_duration=result.generation_duration,
                    self_check=result.self_check,
                ))
                await db.commit()
            except Exception as log_e:
                logger.warning(f"课件 GenerationLog 写入失败（不影响产物）: {log_e}")

        state.update(
            status="done",
            project_id=created["project"]["id"],
            fallback=result.fallback,
            generation_duration=result.generation_duration,
            progress=None,
        )
    except Exception as e:
        logger.error(f"课件生成任务失败: {e}")
        state.update(status="error", error=str(e)[:300], progress=None)


class CoursewareProjectUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=200)
    mode: Optional[Literal["slides", "longform"]] = None
    status: Optional[Literal["draft", "in_editing", "ready_to_present", "archived"]] = None


class CoursewareVersionCreate(BaseModel):
    editor_schema_json: Dict[str, Any]
    rendered_html: Optional[str] = None
    asset_manifest_json: Optional[Dict[str, Any]] = None
    structure_sync_json: Optional[Dict[str, Any]] = None
    change_summary: Optional[str] = Field(None, max_length=500)
    save_type: Literal["autosave", "manual_snapshot", "published_classroom"] = "manual_snapshot"
    parent_version_id: Optional[str] = None


class ComponentDefinitionCreate(BaseModel):
    name: str = Field(..., max_length=200)
    slug: str = Field(..., max_length=200)
    summary: Optional[str] = Field(None, max_length=500)
    preview_cover: Optional[str] = None
    category: Optional[str] = None
    teaching_stage: Optional[str] = None
    subject_tags: Optional[List[str]] = None
    interaction_level: Optional[str] = None
    mode_support: Literal["slides", "longform", "both"] = "both"
    schema_json: Optional[Dict[str, Any]] = None
    render_template_html: Optional[str] = None
    style_bundle: Optional[Dict[str, Any]] = None
    asset_bundle: Optional[Dict[str, Any]] = None
    scope: Literal["personal", "community"] = "personal"
    is_publishable: bool = False
    community_status: Literal["draft", "submitted", "approved", "rejected"] = "draft"


async def _get_owned_project(
    project_id: str,
    current_user: dict,
    db: AsyncSession,
) -> CoursewareProject:
    result = await db.execute(
        select(CoursewareProject).where(
            CoursewareProject.id == project_id,
            CoursewareProject.owner_user_id == current_user["user_id"],
        )
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Courseware project not found")
    return project


async def _create_initial_project_state(
    *,
    title: str,
    source_type: str,
    source_plan_id: Optional[str],
    mode: str,
    template_id: str,
    source_meta: Optional[Dict[str, Any]],
    current_user: dict,
    db: AsyncSession,
    bootstrap_payload: Dict[str, Any],
) -> Dict[str, Any]:
    project_id = str(uuid4())
    profile_id = str(uuid4())
    version_id = str(uuid4())

    project = CoursewareProject(
        id=project_id,
        owner_user_id=current_user["user_id"],
        title=title,
        source_type=source_type,
        source_plan_id=source_plan_id,
        mode=mode,
        template_id=template_id,
        status="in_editing",
        source_meta=source_meta,
        current_version_id=version_id,
        presentation_profile_id=profile_id,
    )
    db.add(project)

    profile = PresentationProfile(
        id=profile_id,
        project_id=project_id,
        mode=mode,
        settings_json=build_default_presentation_settings(mode),
        is_default=True,
    )
    db.add(profile)

    version = CoursewareVersion(
        id=version_id,
        project_id=project_id,
        version_number=1,
        save_type="manual_snapshot",
        editor_schema_json=bootstrap_payload.get("editor_schema_json"),
        rendered_html=bootstrap_payload.get("rendered_html"),
        asset_manifest_json=bootstrap_payload.get("asset_manifest_json") or {"items": [], "count": 0},
        structure_sync_json=bootstrap_payload.get("structure_sync_json") or {},
        change_summary="初始版本",
        created_by=current_user["user_id"],
    )
    db.add(version)

    await db.commit()
    await db.refresh(project)
    await db.refresh(profile)
    await db.refresh(version)

    return {
        "project": project.to_dict(),
        "presentation_profile": profile.to_dict(),
        "current_version": version.to_dict(),
    }


@router.get("")
async def list_courseware_projects(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    result = await db.execute(
        select(CoursewareProject)
        .where(CoursewareProject.owner_user_id == current_user["user_id"])
        .order_by(CoursewareProject.updated_at.desc())
    )
    projects = result.scalars().all()
    return [project.to_dict() for project in projects]


@router.get("/components")
async def list_component_definitions(
    scope: Optional[str] = None,
    category: Optional[str] = None,
    teaching_stage: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    query = select(ComponentDefinition)
    if scope == "personal":
        query = query.where(
            ComponentDefinition.scope == "personal",
            ComponentDefinition.owner_user_id == current_user["user_id"],
        )
    elif scope:
        query = query.where(ComponentDefinition.scope == scope)
    if category:
        query = query.where(ComponentDefinition.category == category)
    if teaching_stage:
        query = query.where(ComponentDefinition.teaching_stage == teaching_stage)

    query = query.order_by(ComponentDefinition.updated_at.desc())
    result = await db.execute(query)
    components = result.scalars().all()
    return [component.to_dict() for component in components]


class ComponentDefinitionUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=200)
    summary: Optional[str] = None
    preview_cover: Optional[str] = None
    category: Optional[str] = None
    teaching_stage: Optional[str] = None
    subject_tags: Optional[List[str]] = None
    schema_json: Optional[Dict[str, Any]] = None
    render_template_html: Optional[str] = None
    style_bundle: Optional[Dict[str, Any]] = None
    asset_bundle: Optional[Dict[str, Any]] = None
    is_publishable: Optional[bool] = None
    community_status: Optional[Literal["draft", "submitted", "approved", "rejected"]] = None


@router.post("/components", status_code=status.HTTP_201_CREATED)
async def create_component_definition(
    request: ComponentDefinitionCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    component = ComponentDefinition(
        id=str(uuid4()),
        owner_user_id=current_user["user_id"],
        scope=request.scope,
        name=request.name,
        slug=request.slug,
        summary=request.summary,
        preview_cover=request.preview_cover,
        category=request.category,
        teaching_stage=request.teaching_stage,
        subject_tags=request.subject_tags or [],
        interaction_level=request.interaction_level,
        mode_support=request.mode_support,
        schema_json=request.schema_json,
        render_template_html=request.render_template_html,
        style_bundle=request.style_bundle,
        asset_bundle=request.asset_bundle,
        is_publishable=request.is_publishable,
        community_status=request.community_status,
    )
    db.add(component)
    await db.commit()
    await db.refresh(component)
    return component.to_dict()


@router.put("/components/{component_id}")
async def update_component_definition(
    component_id: str,
    request: ComponentDefinitionUpdate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    result = await db.execute(
        select(ComponentDefinition).where(
            ComponentDefinition.id == component_id,
            ComponentDefinition.owner_user_id == current_user["user_id"],
        )
    )
    component = result.scalar_one_or_none()
    if not component:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Component not found")
    for key, value in request.model_dump(exclude_unset=True).items():
        setattr(component, key, value)
    await db.commit()
    await db.refresh(component)
    return component.to_dict()


@router.delete("/components/{component_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_component_definition(
    component_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    result = await db.execute(
        select(ComponentDefinition).where(
            ComponentDefinition.id == component_id,
            ComponentDefinition.owner_user_id == current_user["user_id"],
        )
    )
    component = result.scalar_one_or_none()
    if not component:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Component not found")
    await db.delete(component)
    await db.commit()


@router.post("/components/{component_id}/submit")
async def submit_component_to_community(
    component_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    result = await db.execute(
        select(ComponentDefinition).where(
            ComponentDefinition.id == component_id,
            ComponentDefinition.owner_user_id == current_user["user_id"],
        )
    )
    component = result.scalar_one_or_none()
    if not component:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Component not found")
    component.community_status = "submitted"
    component.is_publishable = True
    await db.commit()
    await db.refresh(component)
    return component.to_dict()


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_courseware_project(
    request: CoursewareProjectCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    if request.source_type == "imported_html" and not request.imported_html:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="imported_html is required")

    if request.source_type == "imported_html":
        bootstrap_payload = build_imported_courseware(
            title=request.title,
            mode=request.mode,
            template_id=request.template_id,
            imported_html=request.imported_html or "",
            source_meta=request.source_meta,
        )
    else:
        bootstrap_payload = build_blank_courseware(
            title=request.title,
            mode=request.mode,
            template_id=request.template_id,
            source_meta=request.source_meta,
        )

    return await _create_initial_project_state(
        title=request.title,
        source_type=request.source_type,
        source_plan_id=request.source_plan_id,
        mode=request.mode,
        template_id=request.template_id,
        source_meta=request.source_meta,
        current_user=current_user,
        db=db,
        bootstrap_payload=bootstrap_payload,
    )


@router.post("/from-plan", status_code=status.HTTP_201_CREATED)
async def create_courseware_from_plan(
    request: CoursewareFromPlanCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    # 查询官方教学组件（组件库驱动课件生成）
    components_result = await db.execute(
        select(ComponentDefinition).where(ComponentDefinition.scope == "official")
    )
    official_components = components_result.scalars().all()
    components = [c.to_dict() for c in official_components]

    bootstrap_payload = build_courseware_from_plan(
        title=request.title,
        mode=request.mode,
        template_id=request.template_id,
        plan=request.plan,
        learner_gap=request.learner_gap,
        enhancement_tags=request.enhancement_tags,
        source_meta=request.source_meta,
        components=components,
    )
    return await _create_initial_project_state(
        title=request.title,
        source_type="from_plan",
        source_plan_id=request.source_plan_id,
        mode=request.mode,
        template_id=request.template_id,
        source_meta=request.source_meta,
        current_user=current_user,
        db=db,
        bootstrap_payload=bootstrap_payload,
    )


@router.post("/generate", status_code=status.HTTP_202_ACCEPTED)
async def start_courseware_generation(
    request: CoursewareGenerateRequest,
    current_user: dict = Depends(get_current_user),
):
    """启动 LLM 课件生成（HTML 链路，异步任务），返回 task_id 供轮询"""
    _prune_generation_tasks()
    task_id = uuid4().hex
    _GENERATION_TASKS[task_id] = {
        "status": "pending",
        "progress": "已排队",
        "user_id": current_user["user_id"],
        "created_ts": time.time(),
    }
    asyncio.create_task(_run_html_generation(task_id, request, current_user))
    return {"task_id": task_id}


@router.get("/generate/{task_id}")
async def get_courseware_generation_status(
    task_id: str,
    current_user: dict = Depends(get_current_user),
):
    """轮询课件生成任务状态"""
    state = _GENERATION_TASKS.get(task_id)
    if not state or state.get("user_id") != current_user["user_id"]:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="生成任务不存在或已过期，请重新生成")
    return {
        "task_id": task_id,
        "status": state.get("status"),
        "progress": state.get("progress"),
        "project_id": state.get("project_id"),
        "fallback": state.get("fallback"),
        "generation_duration": state.get("generation_duration"),
        "error": state.get("error"),
    }


@router.get("/{project_id}")
async def get_courseware_project(
    project_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    project = await _get_owned_project(project_id, current_user, db)

    version_result = await db.execute(
        select(CoursewareVersion)
        .where(CoursewareVersion.project_id == project.id)
        .order_by(CoursewareVersion.version_number.desc())
    )
    versions = version_result.scalars().all()

    profile_result = await db.execute(
        select(PresentationProfile).where(PresentationProfile.project_id == project.id)
    )
    profiles = profile_result.scalars().all()

    return {
        **project.to_dict(),
        "versions": [version.to_dict() for version in versions],
        "presentation_profiles": [profile.to_dict() for profile in profiles],
    }


@router.put("/{project_id}")
async def update_courseware_project(
    project_id: str,
    request: CoursewareProjectUpdate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    project = await _get_owned_project(project_id, current_user, db)
    for key, value in request.model_dump(exclude_unset=True).items():
        setattr(project, key, value)
    await db.commit()
    await db.refresh(project)
    return project.to_dict()


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_courseware_project(
    project_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    project = await _get_owned_project(project_id, current_user, db)
    await db.delete(project)
    await db.commit()


@router.get("/{project_id}/versions")
async def list_courseware_versions(
    project_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    project = await _get_owned_project(project_id, current_user, db)
    result = await db.execute(
        select(CoursewareVersion)
        .where(CoursewareVersion.project_id == project.id)
        .order_by(CoursewareVersion.version_number.desc())
    )
    versions = result.scalars().all()
    return [version.to_dict() for version in versions]


@router.post("/{project_id}/versions", status_code=status.HTTP_201_CREATED)
async def create_courseware_version(
    project_id: str,
    request: CoursewareVersionCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    project = await _get_owned_project(project_id, current_user, db)

    result = await db.execute(
        select(func.max(CoursewareVersion.version_number)).where(CoursewareVersion.project_id == project.id)
    )
    latest_version_number = result.scalar() or 0
    version_number = latest_version_number + 1

    version = CoursewareVersion(
        id=str(uuid4()),
        project_id=project.id,
        version_number=version_number,
        parent_version_id=request.parent_version_id or project.current_version_id,
        save_type=request.save_type,
        editor_schema_json=request.editor_schema_json,
        rendered_html=request.rendered_html,
        asset_manifest_json=request.asset_manifest_json or {"items": [], "count": 0},
        structure_sync_json=request.structure_sync_json or {},
        change_summary=request.change_summary,
        created_by=current_user["user_id"],
    )
    db.add(version)

    project.current_version_id = version.id
    project.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(version)
    await db.refresh(project)

    return {
        "project": project.to_dict(),
        "version": version.to_dict(),
    }


@router.get("/{project_id}/versions/{version_id}")
async def get_courseware_version(
    project_id: str,
    version_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    project = await _get_owned_project(project_id, current_user, db)
    result = await db.execute(
        select(CoursewareVersion).where(
            CoursewareVersion.id == version_id,
            CoursewareVersion.project_id == project.id,
        )
    )
    version = result.scalar_one_or_none()
    if not version:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Version not found")
    return version.to_dict()
