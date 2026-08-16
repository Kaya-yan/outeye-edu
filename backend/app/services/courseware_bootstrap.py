"""
教学课件项目初始结构与 HTML 引导生成服务
"""

from datetime import datetime
from html import escape as html_escape
from typing import Any, Dict, List, Optional
from uuid import uuid4

from app.services.analysis.export_service import export_html


def build_default_presentation_settings(mode: str) -> Dict[str, Any]:
    return {
        "mode": mode,
        "allow_fullscreen": True,
        "show_teacher_notes": False,
        "enable_local_interactions": True,
        "enable_step_reveal": True,
        "enable_timer": True,
        "show_navigation": True,
        "theme": "classroom-default",
        "shortcuts": {
            "prev": "ArrowLeft",
            "next": "ArrowRight",
            "reveal": "Space",
            "fullscreen_exit": "Escape",
            "blackout": "KeyB",
            "timer": "KeyT",
            "notes": "KeyN",
            "hide_ui": "KeyH",
        },
    }


def build_courseware_from_plan(
    *,
    title: str,
    mode: str,
    template_id: str,
    plan: Dict[str, Any],
    learner_gap: Optional[Dict[str, Any]] = None,
    enhancement_tags: Optional[List[str]] = None,
    source_meta: Optional[Dict[str, Any]] = None,
    components: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    normalized_plan = dict(plan)
    if learner_gap is not None:
        normalized_plan["learner_gap"] = learner_gap
    if enhancement_tags is not None:
        normalized_plan["tags"] = enhancement_tags

    editor_schema = (
        _build_slides_schema(title, template_id, normalized_plan, source_meta, components)
        if mode == "slides"
        else _build_longform_schema(title, template_id, normalized_plan, source_meta, components)
    )
    structure_sync = _build_structure_sync(editor_schema)
    rendered_html = _render_plan_html(title, normalized_plan)

    return {
        "editor_schema_json": editor_schema,
        "rendered_html": rendered_html,
        "asset_manifest_json": {"items": [], "count": 0},
        "structure_sync_json": structure_sync,
    }


def build_blank_courseware(
    *,
    title: str,
    mode: str,
    template_id: str,
    source_meta: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    page_kind = "slide" if mode == "slides" else "longform"
    page_id = f"page-{uuid4().hex[:8]}"
    editor_schema = {
        "meta": {
            "title": title,
            "mode": mode,
            "template_id": template_id,
            "source_type": "blank_template",
            "created_at": datetime.utcnow().isoformat(),
            "source_meta": source_meta or {},
        },
        "outline": [
            {"id": page_id, "label": "第一页", "source_key": None},
        ],
        "pages": [
            {
                "id": page_id,
                "kind": page_kind,
                "title": "第一页",
                "blocks": [
                    {
                        "id": f"block-{uuid4().hex[:8]}",
                        "type": "title",
                        "label": "课件标题",
                        "editable": "structured",
                        "source_key": None,
                        "content": {"text": title},
                    },
                    {
                        "id": f"block-{uuid4().hex[:8]}",
                        "type": "paragraph",
                        "label": "正文说明",
                        "editable": "free",
                        "source_key": None,
                        "content": {"text": "在这里开始编辑你的教学课件内容。"},
                    },
                ],
            }
        ],
    }
    return {
        "editor_schema_json": editor_schema,
        "rendered_html": _render_fallback_html(title, "在这里开始编辑你的教学课件内容。"),
        "asset_manifest_json": {"items": [], "count": 0},
        "structure_sync_json": _build_structure_sync(editor_schema),
    }


def build_imported_courseware(
    *,
    title: str,
    mode: str,
    template_id: str,
    imported_html: str,
    source_meta: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    page_kind = "slide" if mode == "slides" else "longform"
    page_id = f"page-{uuid4().hex[:8]}"
    editor_schema = {
        "meta": {
            "title": title,
            "mode": mode,
            "template_id": template_id,
            "source_type": "imported_html",
            "created_at": datetime.utcnow().isoformat(),
            "source_meta": source_meta or {},
        },
        "outline": [
            {"id": page_id, "label": "导入页面", "source_key": "imported_html"},
        ],
        "pages": [
            {
                "id": page_id,
                "kind": page_kind,
                "title": "导入页面",
                "blocks": [
                    {
                        "id": f"block-{uuid4().hex[:8]}",
                        "type": "html_embed",
                        "label": "导入 HTML",
                        "editable": "free",
                        "source_key": "imported_html",
                        "content": {"html": imported_html},
                    }
                ],
            }
        ],
    }
    return {
        "editor_schema_json": editor_schema,
        "rendered_html": imported_html,
        "asset_manifest_json": {"items": [], "count": 0},
        "structure_sync_json": _build_structure_sync(editor_schema),
    }


def _build_slides_schema(
    title: str,
    template_id: str,
    plan: Dict[str, Any],
    source_meta: Optional[Dict[str, Any]],
    components: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    pages = []
    outline = []

    def add_page(label: str, source_key: Optional[str], blocks: List[Dict[str, Any]]):
        page_id = f"page-{uuid4().hex[:8]}"
        outline.append({"id": page_id, "label": label, "source_key": source_key})
        pages.append({
            "id": page_id,
            "kind": "slide",
            "title": label,
            "blocks": blocks,
        })

    add_page(
        "封面",
        None,
        [
            _title_block(title, None),
            _meta_block(
                learner_gap=plan.get("learner_gap") or {},
                enhancement_tags=plan.get("tags") or [],
            ),
        ],
    )

    if plan.get("difficulty_overview"):
        add_page(
            "课文难度概述",
            "difficulty_overview",
            [_paragraph_block("课文难度概述", plan.get("difficulty_overview", ""), "difficulty_overview", editable="structured")],
        )

    suggestions = plan.get("teaching_suggestions") or []
    if suggestions:
        add_page(
            "教学建议",
            "teaching_suggestions",
            [_list_block("教学建议", suggestions, "teaching_suggestions", block_type="teaching_suggestions")],
        )

    activities = plan.get("activity_designs") or []
    for index, activity in enumerate(activities, 1):
        blocks = [_activity_block(activity, index, components)]
        add_page(f"活动 {index}", f"activity_designs[{index - 1}]", blocks)

    if plan.get("differentiation"):
        add_page(
            "差异化教学策略",
            "differentiation",
            [_paragraph_block("差异化教学策略", plan.get("differentiation", ""), "differentiation", editable="structured")],
        )

    if plan.get("theoretical_basis"):
        add_page(
            "理论依据",
            "theoretical_basis",
            [_paragraph_block("理论依据", plan.get("theoretical_basis", ""), "theoretical_basis", editable="structured")],
        )

    return {
        "meta": {
            "title": title,
            "mode": "slides",
            "template_id": template_id,
            "source_type": "from_plan",
            "created_at": datetime.utcnow().isoformat(),
            "source_meta": source_meta or {},
        },
        "outline": outline,
        "pages": pages,
    }


def _build_longform_schema(
    title: str,
    template_id: str,
    plan: Dict[str, Any],
    source_meta: Optional[Dict[str, Any]],
    components: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    blocks: List[Dict[str, Any]] = [_title_block(title, None)]
    blocks.append(_meta_block(plan.get("learner_gap") or {}, plan.get("tags") or []))

    if plan.get("difficulty_overview"):
        blocks.append(_paragraph_block("课文难度概述", plan.get("difficulty_overview", ""), "difficulty_overview", editable="structured"))

    suggestions = plan.get("teaching_suggestions") or []
    if suggestions:
        blocks.append(_list_block("教学建议", suggestions, "teaching_suggestions", block_type="teaching_suggestions"))

    activities = plan.get("activity_designs") or []
    for index, activity in enumerate(activities, 1):
        blocks.append(_activity_block(activity, index, components))

    if plan.get("differentiation"):
        blocks.append(_paragraph_block("差异化教学策略", plan.get("differentiation", ""), "differentiation", editable="structured"))

    if plan.get("theoretical_basis"):
        blocks.append(_paragraph_block("理论依据", plan.get("theoretical_basis", ""), "theoretical_basis", editable="structured"))

    page_id = f"page-{uuid4().hex[:8]}"
    return {
        "meta": {
            "title": title,
            "mode": "longform",
            "template_id": template_id,
            "source_type": "from_plan",
            "created_at": datetime.utcnow().isoformat(),
            "source_meta": source_meta or {},
        },
        "outline": [
            {"id": page_id, "label": "主页面", "source_key": "courseware_main"},
        ],
        "pages": [
            {
                "id": page_id,
                "kind": "longform",
                "title": title,
                "blocks": blocks,
            }
        ],
    }


def _build_structure_sync(editor_schema: Dict[str, Any]) -> Dict[str, Any]:
    page_map = []
    for page in editor_schema.get("pages", []):
        block_map = []
        for block in page.get("blocks", []):
            block_map.append({
                "block_id": block.get("id"),
                "source_key": block.get("source_key"),
                "editable": block.get("editable"),
                "type": block.get("type"),
            })
        page_map.append({
            "page_id": page.get("id"),
            "page_title": page.get("title"),
            "blocks": block_map,
        })
    return {"pages": page_map}


def _render_plan_html(title: str, plan: Dict[str, Any]) -> str:
    try:
        buffer = export_html(plan, title)
        return buffer.getvalue().decode("utf-8")
    except Exception:
        return _render_fallback_html(title, plan.get("difficulty_overview", ""))


def _render_fallback_html(title: str, body_text: str) -> str:
    return f"""<!DOCTYPE html>
<html lang=\"zh-CN\">
<head>
  <meta charset=\"UTF-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />
  <title>{html_escape(title)}</title>
  <style>
    body {{ font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 0; background: #f7f9fc; color: #172d4a; }}
    main {{ max-width: 960px; margin: 0 auto; padding: 48px 24px 64px; }}
    h1 {{ font-size: 40px; margin-bottom: 16px; }}
    .card {{ background: #fff; border-radius: 20px; padding: 24px; box-shadow: 0 12px 32px rgba(16,24,40,.08); }}
    p {{ line-height: 1.75; color: #344054; white-space: pre-wrap; }}
  </style>
</head>
<body>
  <main>
    <h1>{html_escape(title)}</h1>
    <div class=\"card\">
      <p>{html_escape(body_text or '教学课件内容将在此显示。')}</p>
    </div>
  </main>
</body>
</html>"""


def _title_block(text: str, source_key: Optional[str]) -> Dict[str, Any]:
    return {
        "id": f"block-{uuid4().hex[:8]}",
        "type": "title",
        "label": "标题",
        "editable": "structured",
        "source_key": source_key,
        "content": {"text": text},
    }


def _paragraph_block(label: str, text: str, source_key: Optional[str], *, editable: str = "free") -> Dict[str, Any]:
    return {
        "id": f"block-{uuid4().hex[:8]}",
        "type": "paragraph",
        "label": label,
        "editable": editable,
        "source_key": source_key,
        "content": {"text": text},
    }


def _list_block(label: str, items: List[str], source_key: Optional[str], *, block_type: str = "list") -> Dict[str, Any]:
    return {
        "id": f"block-{uuid4().hex[:8]}",
        "type": block_type,
        "label": label,
        "editable": "structured",
        "source_key": source_key,
        "content": {"items": items},
    }


def _activity_block(activity: Dict[str, Any], index: int, components: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    block = {
        "id": f"block-{uuid4().hex[:8]}",
        "type": "activity_card",
        "label": f"活动 {index}",
        "editable": "structured",
        "source_key": f"activity_designs[{index - 1}]",
        "content": {
            "name": activity.get("name", f"活动 {index}"),
            "objective": activity.get("objective", ""),
            "steps": activity.get("steps", ""),
            "duration": activity.get("duration", ""),
        },
    }

    # 组件库驱动：若有匹配的官方组件，则引用其 slug 与渲染模板
    if components:
        from app.services.analysis.component_mapper import resolve_component_for_section
        matched = resolve_component_for_section(
            "活动", activity.get("name", ""), components
        )
        if matched:
            block["component_slug"] = matched.get("slug")
            block["component_html"] = matched.get("render_template_html")

    return block


def _meta_block(learner_gap: Dict[str, Any], enhancement_tags: List[str]) -> Dict[str, Any]:
    return {
        "id": f"block-{uuid4().hex[:8]}",
        "type": "meta_info",
        "label": "课件元信息",
        "editable": "structured",
        "source_key": "meta",
        "content": {
            "learner_gap": learner_gap,
            "enhancement_tags": enhancement_tags,
        },
    }
