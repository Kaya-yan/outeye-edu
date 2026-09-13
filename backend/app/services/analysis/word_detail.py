"""
难词教学详情（任务F2 · 提示词模板 word_detail_v1 · 九要素）

白盒难词表只有 word/level/count；音标、词性、语境释义、教学例句、板书建议
由本服务补齐。课文原句不走 LLM——用确定性提取（含词干容错）。
结果写 word_detail_cache 持久缓存：同词再遇零 LLM 成本。
LLM 不可用时返回缓存命中部分 + fallback=True，缺失字段留空。
"""

import asyncio
import json
import re
from typing import Any, Dict, List, Tuple
from loguru import logger

from app.services.prompt_manager import render_prompt

PROMPT_NAME = "word_detail_v1"
MAX_WORDS_PER_CALL = 12
MAX_CONTEXT_CHARS = 3000
DETAIL_FIELDS = ("phonetic", "pos", "gloss", "teaching_example", "board_note")


def extract_original_sentence(text: str, word: str) -> str:
    """确定性提取课文原句：优先整词匹配，退化为词干前缀匹配（复数/时态变体）。"""
    if not text or not word:
        return ""
    sentences = re.split(r"(?<=[.!?。！？])\s+|\n+", text)
    exact = re.compile(r"\b" + re.escape(word) + r"\b", re.IGNORECASE)
    for s in sentences:
        if exact.search(s):
            return s.strip()[:300]
    stem = word[: max(3, len(word) - 2)]
    fuzzy = re.compile(r"\b" + re.escape(stem) + r"\w{0,3}\b", re.IGNORECASE)
    for s in sentences:
        if fuzzy.search(s):
            return s.strip()[:300]
    return ""


def _extract_details(answer: str) -> List[Dict[str, str]]:
    blocks = re.findall(r"```json\s*(.*?)\s*```", answer, re.DOTALL | re.IGNORECASE)
    for block in blocks:
        payload = _try_parse(block)
        if payload is not None:
            return payload
    m = re.search(r"\{.*\}", answer, re.DOTALL)
    if m:
        payload = _try_parse(m.group(0))
        if payload is not None:
            return payload
    return []


def _try_parse(raw: str) -> List[Dict[str, str]]:
    try:
        words = json.loads(raw).get("words")
    except (json.JSONDecodeError, AttributeError):
        return []
    if not isinstance(words, list):
        return []
    cleaned: List[Dict[str, str]] = []
    for w in words:
        if not isinstance(w, dict):
            continue
        item = {k: str(w.get(k, "")).strip() for k in DETAIL_FIELDS}
        item["word"] = str(w.get("word", "")).strip().lower()
        if item["word"] and any(item[k] for k in DETAIL_FIELDS):
            cleaned.append(item)
    return cleaned


async def _read_cache(words: List[str], lang: str) -> Dict[str, Dict[str, str]]:
    from sqlalchemy import select

    from app.core.database import AsyncSessionLocal
    from app.models.analysis import WordDetailCache

    cached: Dict[str, Dict[str, str]] = {}
    async with AsyncSessionLocal() as db:
        rows = (
            await db.execute(
                select(WordDetailCache.word, WordDetailCache.payload_json).where(
                    WordDetailCache.lang == lang,
                    WordDetailCache.word.in_(words),
                )
            )
        ).fetchall()
    for word, payload_json in rows:
        try:
            cached[word] = json.loads(payload_json)
        except json.JSONDecodeError:
            continue
    return cached


async def _write_cache(details: List[Dict[str, str]], lang: str) -> None:
    from app.core.database import AsyncSessionLocal
    from app.models.analysis import WordDetailCache

    try:
        async with AsyncSessionLocal() as db:
            for item in details:
                payload = {k: item.get(k, "") for k in DETAIL_FIELDS}
                db.add(WordDetailCache(
                    word=item["word"], lang=lang,
                    payload_json=json.dumps(payload, ensure_ascii=False),
                ))
            await db.commit()
    except Exception as e:
        logger.warning(f"word_detail_cache 写入失败（不影响详情结果）: {e}")


def _llm_details(words: List[str], context: str) -> List[Dict[str, str]]:
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

    system_prompt, _ = render_prompt(PROMPT_NAME)
    _, user_prompt = render_prompt(
        PROMPT_NAME,
        word_count=len(words),
        words_block=_esc("\n".join(words)),
        context_excerpt=_esc(context[:MAX_CONTEXT_CHARS]),
    )
    answer, _usage = generator._generate_with_api([
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ])
    wanted = set(words)
    return [w for w in _extract_details(answer) if w["word"] in wanted]


async def fetch_word_details(
    words: List[str], text: str = "", lang: str = "en"
) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Any]]:
    """批量取难词详情。返回 (details, meta)；meta = {cache_hits, llm_generated, fallback}。
    每词详情含 DETAIL_FIELDS + original_sentence（确定性提取，不入缓存）。"""
    cleaned = [w for w in dict.fromkeys(w.lower().strip() for w in words) if w][:30]
    if not cleaned:
        return {}, {"cache_hits": 0, "llm_generated": 0, "fallback": False}

    try:
        cached = await _read_cache(cleaned, lang)
    except Exception as e:
        logger.warning(f"word_detail_cache 读取失败（按未缓存处理）: {e}")
        cached = {}

    misses = [w for w in cleaned if w not in cached]
    generated: List[Dict[str, str]] = []
    if misses:
        try:
            for i in range(0, len(misses), MAX_WORDS_PER_CALL):
                batch = misses[i:i + MAX_WORDS_PER_CALL]
                generated.extend(await asyncio.to_thread(_llm_details, batch, text))
        except Exception as e:
            logger.warning(f"难词详情 LLM 生成失败，保留缓存命中部分: {type(e).__name__}: {e}")
        if generated:
            await _write_cache(generated, lang)
            for item in generated:
                cached[item["word"]] = {k: item.get(k, "") for k in DETAIL_FIELDS}

    generated_words = {g["word"] for g in generated}
    details: Dict[str, Dict[str, Any]] = {}
    for w in cleaned:
        payload = cached.get(w, {})
        details[w] = {
            **{k: payload.get(k, "") for k in DETAIL_FIELDS},
            "original_sentence": extract_original_sentence(text, w),
            "source": "llm" if w in generated_words else "cached" if payload else "miss",
        }
    meta = {
        "cache_hits": len(cached) - len(generated),
        "llm_generated": len(generated),
        "fallback": bool(misses) and not generated,
    }
    return details, meta
