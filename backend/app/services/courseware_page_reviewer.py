"""S5 教研员评审：逐页第二层内容质检

生成后逐页复核（分数锚点按金标准精讲页校准）：低于阈值的页面带意见重写
≤2 轮，保留 score 最高版本；DeepSeek 调用指数退避；任何复核异常都保留
原稿、绝不阻塞课件产出。开关 PAGE_REVIEWER_ENABLED 关闭即整层跳过。
"""

import json
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable, Dict, List, Optional, Tuple

from loguru import logger

from app.services.courseware_llm_generator import (
    KIND_LABELS,
    PAGE_PROMPT_NAME,
    _build_page_prompt,
    _esc,
    _regen_page,
)
from app.services.prompt_manager import prompt_version, render_prompt

REVIEWER_PROMPT_NAME = "courseware_page_reviewer_v1"
REVIEW_PASS_SCORE = 7.0
MAX_REVIEW_REWRITES = 2
_REVIEW_CONCURRENCY = 3


def _call_with_backoff(generator: Any, messages: List[Dict[str, str]], tries: int = 3, base_delay: float = 0.6) -> str:
    """评审调用的指数退避：DeepSeek 偶发超时/限流时 0.6s→1.2s→2.4s 重试"""
    last: Optional[Exception] = None
    for i in range(tries):
        try:
            answer, _ = generator._generate_with_api(messages)
            return answer
        except Exception as e:
            last = e
            if i < tries - 1:
                time.sleep(base_delay * (2 ** i))
    assert last is not None
    raise last


def _parse_review(answer: str) -> Optional[Dict[str, Any]]:
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", answer, re.S)
    raw = m.group(1) if m else answer.strip()
    try:
        data = json.loads(raw)
    except Exception:
        return None
    score = data.get("score")
    if isinstance(score, bool) or not isinstance(score, (int, float)):
        return None
    score = max(0.0, min(10.0, float(score)))
    # score 与 verdict 不一致时以 score 为准（程序强制校正）
    verdict = "pass" if score >= REVIEW_PASS_SCORE else "fail"

    def _clip(key: str) -> List[str]:
        return [str(x) for x in (data.get(key) or []) if str(x).strip()][:6]

    return {"score": score, "verdict": verdict, "problems": _clip("problems"), "suggestions": _clip("suggestions")}


def _build_review_prompt(spec: Dict[str, Any], page: Any, prompt_kwargs: Dict[str, Any], page_no: int, total: int) -> str:
    idxs = spec.get("para") or []
    paragraphs: List[str] = prompt_kwargs.get("paragraphs") or []
    slices: List[Dict[str, Any]] = prompt_kwargs.get("slices") or []
    para_block = "（本页无段落锚点）"
    slices_block = "-（本页无段落锚点）"
    if idxs:
        para_block = "\n\n".join(
            f"【第{i}段】\n{_esc(paragraphs[i - 1])}" for i in idxs if 0 < i <= len(paragraphs)
        ) or "（本页无段落锚点）"
        parts = []
        for s in (x for x in slices if x["index"] in idxs):
            words = "、".join(s["difficult_words"][:8]) or "（无）"
            sents = "\n  ".join(_esc(x) for x in s["long_sentences"]) or "（本段无超阈值长难句）"
            parts.append(f"- 第{s['index']}段 难点词：{words}\n  长难句候选：\n  {sents}")
        slices_block = "\n".join(parts)
    _, user_prompt = render_prompt(
        REVIEWER_PROMPT_NAME,
        page_no=page_no,
        total=total,
        kind_label=KIND_LABELS.get(spec.get("kind"), spec.get("kind") or "未知"),
        page_title=_esc(page.title or spec.get("title") or ""),
        page_intent=_esc(page.intent or spec.get("intent") or ""),
        para_block=para_block,
        slices_block=slices_block,
        page_html=page.html,
    )
    return user_prompt


def _review_one_page(
    generator: Any,
    spec: Dict[str, Any],
    page: Any,
    prompt_kwargs: Dict[str, Any],
    page_no: int,
    total: int,
    context_nav: str,
) -> Tuple[Any, Dict[str, Any]]:
    stats: Dict[str, Any] = {"score": None, "verdict": "unreviewed", "rewrites": 0, "problems": []}
    try:
        reviewer_system, _ = render_prompt(REVIEWER_PROMPT_NAME)
        review = _parse_review(
            _call_with_backoff(generator, [
                {"role": "system", "content": reviewer_system},
                {"role": "user", "content": _build_review_prompt(spec, page, prompt_kwargs, page_no, total)},
            ])
        )
        if review is None:
            return page, stats
        stats.update(score=review["score"], verdict=review["verdict"], problems=review["problems"])

        best_page, best_score, best_review = page, review["score"], review
        page_system, _ = render_prompt(PAGE_PROMPT_NAME)
        page_prompt = _build_page_prompt(spec, page_no=page_no, total=total, context_nav=context_nav, **prompt_kwargs)
        for _round in range(MAX_REVIEW_REWRITES):
            if best_review["verdict"] == "pass":
                break
            problems = best_review["problems"] or best_review["suggestions"] or [
                f"复核得分 {best_review['score']} 低于 {REVIEW_PASS_SCORE}，请整体提升内容质量与教学要素完整性"
            ]
            stats["rewrites"] += 1
            rewritten = _regen_page(generator, page_system, page_prompt, best_page, page_no, problems)
            if rewritten is None:
                break
            rewritten.title = rewritten.title or spec.get("title") or ""
            rewritten.intent = spec.get("intent") or rewritten.intent
            review2 = _parse_review(
                _call_with_backoff(generator, [
                    {"role": "system", "content": reviewer_system},
                    {"role": "user", "content": _build_review_prompt(spec, rewritten, prompt_kwargs, page_no, total)},
                ])
            )
            if review2 is None:
                break
            if review2["score"] > best_score:
                best_page, best_score = rewritten, review2["score"]
            best_review = review2
            stats.update(score=best_score, verdict=best_review["verdict"], problems=best_review["problems"])
        return best_page, stats
    except Exception as e:
        logger.warning(f"课件第 {page_no} 页复核异常，保留原稿: {e}")
        return page, stats


def review_pages(
    generator: Any,
    blueprint: List[Dict[str, Any]],
    prompt_kwargs: Dict[str, Any],
    pages: List[Any],
    page_infos: Dict[int, Dict[str, Any]],
    progress_cb: Optional[Callable[[str], None]] = None,
) -> Tuple[List[Any], Dict[str, Any]]:
    """逐页复核（3 路并发）：fail 带意见重写 ≤2 轮，保留 score 最高版；进度文案含页号"""

    def _progress(msg: str) -> None:
        if progress_cb:
            try:
                progress_cb(msg)
            except Exception:
                pass

    total = len(pages)
    results: Dict[int, Any] = {}
    stats: Dict[int, Dict[str, Any]] = {}
    with ThreadPoolExecutor(max_workers=_REVIEW_CONCURRENCY) as pool:
        futures = {}
        for i, (spec, page) in enumerate(zip(blueprint, pages)):
            if page_infos.get(i, {}).get("stub"):
                results[i] = page
                stats[i] = {"score": None, "verdict": "skipped_stub", "rewrites": 0, "problems": []}
                continue
            prev_t = (blueprint[i - 1].get("title") or KIND_LABELS.get(blueprint[i - 1]["kind"], "未知")) if i else "（无）"
            next_t = (blueprint[i + 1].get("title") or KIND_LABELS.get(blueprint[i + 1]["kind"], "未知")) if i + 1 < total else "（无）"
            context_nav = f"前一页「{prev_t}」，后一页「{next_t}」"
            futures[pool.submit(_review_one_page, generator, spec, page, prompt_kwargs, i + 1, total, context_nav)] = i
        done = 0
        for fut in as_completed(futures):
            i = futures[fut]
            done += 1
            try:
                results[i], stats[i] = fut.result()
            except Exception as e:
                logger.warning(f"课件第 {i + 1} 页复核任务异常，保留原稿: {e}")
                results[i] = pages[i]
                stats[i] = {"score": None, "verdict": "unreviewed", "rewrites": 0, "problems": []}
            _progress(f"正在复核：第 {i + 1} 页（{done}/{total}）")

    scores = [s["score"] for s in stats.values() if s.get("score") is not None]
    summary = {
        "version": prompt_version(REVIEWER_PROMPT_NAME),
        "pass_score": REVIEW_PASS_SCORE,
        "avg_score": round(sum(scores) / len(scores), 2) if scores else None,
        "rewritten_pages": [i + 1 for i in range(total) if stats.get(i, {}).get("rewrites")],
        "unreviewed_pages": [i + 1 for i in range(total) if stats.get(i, {}).get("verdict") == "unreviewed"],
        "still_failing_pages": [i + 1 for i in range(total) if stats.get(i, {}).get("verdict") == "fail"],
        "pages": [
            {"page": i + 1, **stats.get(i, {"score": None, "verdict": "unreviewed", "rewrites": 0, "problems": []})}
            for i in range(total)
        ],
    }
    return [results[i] for i in range(total)], summary
