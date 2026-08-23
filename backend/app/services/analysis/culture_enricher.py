"""
文化背景 LLM 具体化引擎（提示词模板 culture_background_v1 · 九要素）

白盒检测保持确定性、秒级返回；检测到文化元素后，本模块用 LLM 把
模板化的"教学建议"文案替换为具体事实性背景（起源/年代/地点/当代形态），
让教师读完即掌握知识点本身。LLM 不可用或解析失败时保留原解释，
fallback=True 由前端标注"通用建议"，绝不静默降级。
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List
from loguru import logger
import json
import re
import time

from app.services.prompt_manager import render_prompt, prompt_version
from app.services.analysis.fusion_generator import _esc, prepare_text

PROMPT_NAME = "culture_background_v1"


@dataclass
class CultureEnrichResult:
    items: List[Dict[str, Any]]          # 富化后的文化元素列表
    prompt_version: str = ""
    model: str = ""
    fallback: bool = True
    self_check: Dict[str, Any] = field(default_factory=dict)
    generation_duration: float = 0.0


def _format_elements_block(elements: List[Dict[str, Any]]) -> str:
    lines = []
    for i, e in enumerate(elements, 1):
        lines.append(
            f"{i}. 关键词：{e.get('keyword', '')}｜类别：{e.get('category', '未分类')}｜课文语境：{e.get('context', '（未提供）')}"
        )
    return "\n".join(lines)


def _extract_json(answer: str) -> Dict[str, Any]:
    """提取 ```json 代码块；无围栏时退而取首个平衡的 {...} 片段"""
    blocks = re.findall(r"```json\s*(.*?)\s*```", answer, re.DOTALL | re.IGNORECASE)
    for block in blocks:
        try:
            return json.loads(block)
        except json.JSONDecodeError:
            continue
    depth = 0
    start = -1
    for i, ch in enumerate(answer):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start >= 0:
                try:
                    return json.loads(answer[start : i + 1])
                except json.JSONDecodeError:
                    start = -1
    return {}


def _merge_items(elements: List[Dict[str, Any]], items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """按关键词（大小写不敏感）回填 background/text_link/teaching_hook"""
    by_kw = {}
    for it in items or []:
        kw = str(it.get("keyword", "")).strip().lower()
        if kw and kw not in by_kw:
            by_kw[kw] = it
    merged = []
    for e in elements:
        enriched = dict(e)
        it = by_kw.get(str(e.get("keyword", "")).strip().lower())
        if it:
            bg = str(it.get("background", "")).strip()
            link = str(it.get("text_link", "")).strip()
            hook = str(it.get("teaching_hook", "")).strip()
            parts = [p for p in (bg, link) if p]
            if parts:
                enriched["explanation"] = "\n".join(parts)
            if hook:
                enriched["teaching_hook"] = hook
            enriched["enriched"] = True
        merged.append(enriched)
    return merged


def enrich_cultural_elements(
    *,
    text: str,
    language_name: str,
    elements: List[Dict[str, Any]],
) -> CultureEnrichResult:
    """
    用 LLM 生成具体事实性文化背景，回填到检测到的文化元素。

    elements 形如白盒分析返回的 cultural_elements：
    [{category, keyword, context, explanation}]。
    失败时原样返回并 fallback=True。
    """
    start_time = time.time()
    version = prompt_version(PROMPT_NAME)
    elements = elements or []
    if not elements:
        return CultureEnrichResult(
            items=[],
            prompt_version=version,
            model="no-op",
            fallback=False,
            generation_duration=round(time.time() - start_time, 2),
        )

    model_name = "template-fallback"
    try:
        _, user_prompt = render_prompt(
            PROMPT_NAME,
            language_name=_esc(language_name or "英语"),
            element_count=len(elements),
            full_text=_esc(prepare_text(text or "")),
            elements_block=_esc(_format_elements_block(elements)),
        )

        from app.services.rag import RAGGenerator
        from app.core.config import settings

        model_name = getattr(settings, "LLM_MODEL", "deepseek-chat")
        generator = RAGGenerator(
            api_key=getattr(settings, "LLM_API_KEY", None),
            api_base=getattr(settings, "LLM_BASE_URL", None),
            model=model_name,
            max_tokens=4096,
            temperature=0.4,
        )

        if not generator.use_api:
            logger.warning("LLM 不可用，文化背景保留通用建议")
            return CultureEnrichResult(
                items=elements,
                prompt_version=version,
                model=model_name,
                fallback=True,
                generation_duration=round(time.time() - start_time, 2),
            )

        system_prompt, _ = render_prompt(PROMPT_NAME)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        answer, _usage = generator._generate_with_api(messages)

        payload = _extract_json(answer)
        items = payload.get("items")
        if not isinstance(items, list) or not items:
            raise ValueError("LLM 输出缺少 items 数组")

        merged = _merge_items(elements, items)
        matched = sum(1 for m in merged if m.get("enriched"))
        if matched == 0:
            raise ValueError("关键词回填全部失败（LLM 输出与检测关键词不匹配）")

        self_check = payload.get("self_check") or {}
        self_check["matched"] = f"{matched}/{len(elements)}"
        return CultureEnrichResult(
            items=merged,
            prompt_version=version,
            model=model_name,
            fallback=False,
            self_check=self_check,
            generation_duration=round(time.time() - start_time, 2),
        )
    except Exception as e:
        logger.warning(f"文化背景具体化失败，保留通用建议: {type(e).__name__}: {e}")
        return CultureEnrichResult(
            items=elements,
            prompt_version=version,
            model="template-fallback",
            fallback=True,
            generation_duration=round(time.time() - start_time, 2),
        )
