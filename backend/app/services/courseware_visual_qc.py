"""S6 视觉质检闭环：截图 → 多模态查缺陷 → 问题页重生成一轮

playwright 串行逐页截图（jpeg q70）→ DashScope Qwen-VL 并发 2 查可见
视觉缺陷 → 有缺陷的页面重生成一轮（带缺陷清单）。整层受硬超时预算
（默认 240s）熔断；chromium / VL key / 网络任一不可用都优雅降级，
绝不阻塞课件产出。开关 VISUAL_QC_ENABLED 关闭即整层跳过。
"""

import base64
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Dict, List, Optional, Tuple

from loguru import logger

from app.services.prompt_manager import prompt_version, render_prompt

VISUAL_QC_PROMPT_NAME = "courseware_visual_qc_v1"
VISUAL_BUDGET_SECONDS = 240.0
VL_CONCURRENCY = 2


def _screenshot_pages_real(docs: List[str], deadline: float) -> Tuple[List[Optional[bytes]], Optional[str]]:
    """串行逐页截图：每份单页文档渲染后按 section.page 元素截图（jpeg q70）"""
    from playwright.sync_api import sync_playwright

    shots: List[Optional[bytes]] = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            ctx = browser.new_page(viewport={"width": 1280, "height": 800}, device_scale_factor=1)
            for doc in docs:
                if time.time() > deadline:
                    shots.append(None)
                    continue
                ctx.set_content(doc, wait_until="load")
                shots.append(ctx.locator("section.page").first.screenshot(type="jpeg", quality=70))
        finally:
            browser.close()
    return shots, None


_screenshot_pages = _screenshot_pages_real


def _vl_check_real(shot: bytes, prompt: str) -> Optional[List[str]]:
    """DashScope Qwen-VL 单页视觉检查；失败返回 None（该页记未检）"""
    from openai import OpenAI

    from app.core.config import settings

    if not settings.VISION_API_KEY:
        return None
    client = OpenAI(api_key=settings.VISION_API_KEY, base_url=settings.VISION_BASE_URL, timeout=60.0)
    resp = client.chat.completions.create(
        model=settings.VISION_MODEL,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64.b64encode(shot).decode()}"}},
                {"type": "text", "text": prompt},
            ],
        }],
        temperature=0.1,
        max_tokens=400,
    )
    answer = (resp.choices[0].message.content or "").strip() if resp.choices else ""
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", answer, re.S)
    raw = m.group(1) if m else answer
    try:
        data = json.loads(raw)
    except Exception:
        return None
    issues = [str(x) for x in (data.get("issues") or []) if str(x).strip()]
    return issues[:5]


_vl_check = _vl_check_real


def run_visual_qc(
    pages: List[Any],
    *,
    blueprint: List[Dict[str, Any]],
    make_doc: Callable[[Any], str],
    regen_page: Callable[[int, Any, List[str]], Optional[Any]],
    kind_labels: Optional[Dict[str, str]] = None,
    progress_cb: Optional[Callable[[str], None]] = None,
    budget_seconds: float = VISUAL_BUDGET_SECONDS,
) -> Tuple[List[Any], Dict[str, Any]]:
    """视觉质检入口：返回（可能被重生成的页面列表, 摘要）；任何异常降级不阻塞"""

    def _progress(msg: str) -> None:
        if progress_cb:
            try:
                progress_cb(msg)
            except Exception:
                pass

    from app.core.config import settings

    kind_labels = kind_labels or {}
    summary: Dict[str, Any] = {
        "enabled": True,
        "version": prompt_version(VISUAL_QC_PROMPT_NAME),
        "model": getattr(settings, "VISION_MODEL", "qwen-vl-plus"),
        "checked_pages": [],
        "unchecked_pages": [],
        "issue_pages": [],
        "issues": {},
        "regenerated_pages": [],
        "deadline_hit": False,
    }
    pages = list(pages)
    total = len(pages)
    deadline = time.time() + budget_seconds
    try:
        if not getattr(settings, "VISION_API_KEY", ""):
            summary["skipped"] = "未配置 VISION_API_KEY"
            return pages, summary

        docs = [make_doc(pg) for pg in pages]
        shots, err = _screenshot_pages(docs, deadline)
        if err:
            summary["error"] = err
            return pages, summary

        def _check_one(i: int) -> Tuple[int, Optional[List[str]]]:
            shot = shots[i]
            if shot is None:
                return i, None
            try:
                spec = blueprint[i] if i < len(blueprint) else {}
                _, prompt = render_prompt(
                    VISUAL_QC_PROMPT_NAME,
                    page_no=i + 1,
                    total=total,
                    kind_label=kind_labels.get(spec.get("kind", ""), spec.get("kind") or "未知"),
                )
                return i, _vl_check(shot, prompt)
            except Exception as e:
                logger.warning(f"视觉质检第 {i + 1} 页 VL 调用失败（记未检）: {e}")
                return i, None

        with ThreadPoolExecutor(max_workers=VL_CONCURRENCY) as pool:
            results = dict(pool.map(_check_one, range(total)))

        for i in range(total):
            issues = results.get(i)
            if issues is None:
                summary["unchecked_pages"].append(i + 1)
                continue
            summary["checked_pages"].append(i + 1)
            if not issues:
                continue
            summary["issue_pages"].append(i + 1)
            summary["issues"][str(i + 1)] = issues
            if time.time() >= deadline:
                summary["deadline_hit"] = True
                continue
            _progress(f"视觉质检：第 {i + 1} 页发现 {len(issues)} 处视觉问题，正在重新生成…")
            try:
                rewritten = regen_page(i, pages[i], issues)
            except Exception as e:
                logger.warning(f"视觉质检第 {i + 1} 页重生成异常（保留原稿）: {e}")
                rewritten = None
            if rewritten is not None:
                pages[i] = rewritten
                summary["regenerated_pages"].append(i + 1)
        return pages, summary
    except Exception as e:
        logger.warning(f"视觉质检整体异常，跳过: {e}")
        summary["error"] = str(e)[:200]
        return pages, summary
