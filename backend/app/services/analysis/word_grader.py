"""
词汇 CEFR 兜底分级（F4.3 · 提示词模板 word_grading_v1 · 九要素）

白盒确定性分级 + 专有名词分桶后的残差（低频/生僻词）交给 LLM
批量定级，结果写 word_level_cache 持久缓存：同词再遇零成本。
LLM 不可用时返回空结果并 fallback=True，白盒原样保留未分级。
"""

import asyncio
import re
from typing import Any, Dict, List, Tuple
from loguru import logger

from app.services.prompt_manager import render_prompt

PROMPT_NAME = "word_grading_v1"
VALID_LEVELS = {"A1", "A2", "B1", "B2", "C1", "C2"}
MAX_WORDS_PER_CALL = 60


def _extract_levels(answer: str) -> Dict[str, str]:
    import json

    blocks = re.findall(r"```json\s*(.*?)\s*```", answer, re.DOTALL | re.IGNORECASE)
    for block in blocks:
        try:
            payload = json.loads(block)
            levels = payload.get("levels")
            if isinstance(levels, dict):
                return {str(k).lower(): str(v).upper() for k, v in levels.items()}
        except json.JSONDecodeError:
            continue
    m = re.search(r"\{.*\}", answer, re.DOTALL)
    if m:
        try:
            payload = json.loads(m.group(0))
            levels = payload.get("levels")
            if isinstance(levels, dict):
                return {str(k).lower(): str(v).upper() for k, v in levels.items()}
        except json.JSONDecodeError:
            pass
    return {}


async def _read_cache(words: List[str], lang: str) -> Dict[str, str]:
    from sqlalchemy import select

    from app.core.database import AsyncSessionLocal
    from app.models.analysis import WordLevelCache

    cached: Dict[str, str] = {}
    async with AsyncSessionLocal() as db:
        rows = (
            await db.execute(
                select(WordLevelCache.word, WordLevelCache.level).where(
                    WordLevelCache.lang == lang,
                    WordLevelCache.word.in_(words),
                )
            )
        ).fetchall()
    for word, level in rows:
        cached[word] = level
    return cached


async def _write_cache(levels: Dict[str, str], lang: str) -> None:
    from app.core.database import AsyncSessionLocal
    from app.models.analysis import WordLevelCache

    try:
        async with AsyncSessionLocal() as db:
            for word, level in levels.items():
                db.add(WordLevelCache(word=word, lang=lang, level=level, source="llm"))
            await db.commit()
    except Exception as e:
        logger.warning(f"word_level_cache 写入失败（不影响分级结果）: {e}")


def _llm_grade(words: List[str], lang: str) -> Dict[str, str]:
    from app.services.rag import RAGGenerator
    from app.core.config import settings

    generator = RAGGenerator(
        api_key=getattr(settings, "LLM_API_KEY", None),
        api_base=getattr(settings, "LLM_BASE_URL", None),
        model=getattr(settings, "LLM_MODEL", "deepseek-chat"),
        max_tokens=4096,
        temperature=0.2,
    )
    if not generator.use_api:
        raise RuntimeError("LLM 不可用")

    from app.services.analysis.fusion_generator import _esc

    _, user_prompt = render_prompt(
        PROMPT_NAME,
        word_count=len(words),
        words_block=_esc("\n".join(words)),
    )
    system_prompt, _ = render_prompt(PROMPT_NAME)
    answer, _usage = generator._generate_with_api([
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ])
    levels = _extract_levels(answer)
    return {w: lv for w, lv in levels.items() if w in set(words) and lv in VALID_LEVELS}


async def grade_ungraded_words(words: List[str], lang: str = "en") -> Tuple[Dict[str, str], Dict[str, Any]]:
    """
    对未分级词批量定级。返回 (levels, meta)：
    meta = {cache_hits, llm_graded, fallback}。失败时 levels={} fallback=True。
    """
    words = [w.lower() for w in dict.fromkeys(words) if w][:MAX_WORDS_PER_CALL]
    if not words:
        return {}, {"cache_hits": 0, "llm_graded": 0, "fallback": False}

    try:
        cached = await _read_cache(words, lang)
    except Exception as e:
        logger.warning(f"word_level_cache 读取失败（按未缓存处理）: {e}")
        cached = {}

    misses = [w for w in words if w not in cached]
    if not misses:
        return cached, {"cache_hits": len(cached), "llm_graded": 0, "fallback": False}

    try:
        graded = await asyncio.to_thread(_llm_grade, misses, lang)
    except Exception as e:
        logger.warning(f"LLM 兜底分级失败，保留未分级: {type(e).__name__}: {e}")
        return cached, {"cache_hits": len(cached), "llm_graded": 0, "fallback": True}

    if graded:
        await _write_cache(graded, lang)
    merged = {**cached, **graded}
    return merged, {"cache_hits": len(cached), "llm_graded": len(graded), "fallback": False}


def merge_levels_into_result(result, levels: Dict[str, str]) -> int:
    """把等级合并回白盒结果：未分级计数移入对应档，难词表 level 更新。返回合并词数。"""
    if not levels:
        return 0
    band_of = {"A1": "A1-A2", "A2": "A1-A2", "B1": "B1-B2", "B2": "B1-B2", "C1": "C1-C2", "C2": "C1-C2"}
    dist = result.vocabulary.cefr_distribution
    merged = 0
    for w in result.vocabulary.difficult_words:
        level = levels.get(w.word.lower())
        if w.level == "unknown" and level:
            band = band_of.get(level)
            if not band:
                continue
            count = w.count or 1
            dist["未分级"] = max(0, dist.get("未分级", 0) - count)
            dist[band] = dist.get(band, 0) + count
            w.level = level
            merged += 1
    return merged
