"""S6 视觉质检闭环（两相）：溢出硬关卡（本地几何）+ VL 多模态检查

相 A 溢出硬关卡（OVERFLOW_GATE_ENABLED，默认开，纯本地零外部依赖）：
截图环节在 chromium 内量 section.page 的 scrollHeight - clientHeight（overflow:hidden
下 scrollHeight 仍报告被裁内容全高）；超页页带「内容超页约 X%」反馈重生成，每页最多
2 轮，仍超则保留并记录。chromium/playwright 不可用时 ERROR 级日志 + summary 记录
（chromium 是部署硬依赖，不做静态估算兜底，诚实可见）。

相 B VL 视觉检查（VISUAL_QC_ENABLED 门控 + VISION_API_KEY 必需）：
DashScope Qwen-VL 并发 2 查可见视觉缺陷 → 有缺陷的页面重生成一轮（带缺陷清单）。

两相共享硬超时预算（默认 240s）熔断；任何异常降级，绝不阻塞课件产出。
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

PAGE_DESIGN_HEIGHT = 720
OVERFLOW_PX_THRESHOLD = 12
OVERFLOW_MAX_ROUNDS = 2


def _screenshot_pages_real(docs: List[str], deadline: float) -> Tuple[List[Optional[bytes]], List[Optional[int]], Optional[str]]:
    """串行逐页截图+溢出测量：每份单页文档渲染后对 section.page 截图（jpeg q70），
    并量 scrollHeight - clientHeight 得溢出像素；无溢出为 0。失败返回错误串。"""
    try:
        from playwright.sync_api import sync_playwright
    except Exception as e:
        return [], [], f"playwright 未安装: {e}"
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            try:
                ctx = browser.new_page(viewport={"width": 1280, "height": 800}, device_scale_factor=1)
                shots: List[Optional[bytes]] = []
                overflows: List[Optional[int]] = []
                for doc in docs:
                    if time.time() >= deadline:
                        shots.append(None)
                        overflows.append(None)
                        continue
                    ctx.set_content(doc, wait_until="load")
                    el = ctx.locator("section.page").first
                    shots.append(el.screenshot(type="jpeg", quality=70))
                    overflows.append(el.evaluate("e => e.scrollHeight - e.clientHeight"))
            finally:
                browser.close()
        return shots, overflows, None
    except Exception as e:
        return [], [], f"chromium 截图失败: {e}"


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


def _overflow_pct(px: int) -> int:
    return max(1, round(px / PAGE_DESIGN_HEIGHT * 100))


def _overflow_problem(px: int) -> str:
    return (
        f"内容超页约 {_overflow_pct(px)}%（版心高 720px，本页内容超出约 {px}px，超出部分会被裁剪不可见）。"
        "请精简本页内容（删减次要讲解、缩短例句、合并条目），确保一屏放得下；"
        "若教学容量确实放不下，请精简后在页内说明需要拆页，不要硬塞。"
    )


def run_visual_qc(
    pages: List[Any],
    *,
    blueprint: List[Dict[str, Any]],
    make_doc: Callable[[Any], str],
    regen_page: Callable[[int, Any, List[str]], Optional[Any]],
    kind_labels: Optional[Dict[str, str]] = None,
    progress_cb: Optional[Callable[[str], None]] = None,
    budget_seconds: float = VISUAL_BUDGET_SECONDS,
    vl_enabled: bool = True,
    gate_enabled: bool = True,
) -> Tuple[List[Any], Dict[str, Any]]:
    """视觉质检入口（两相）：返回（可能被重生成的页面列表, 摘要）；任何异常降级不阻塞"""

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
        "overflow": {
            "gate_version": "geo-v1",
            "threshold_px": OVERFLOW_PX_THRESHOLD,
            "max_rounds": OVERFLOW_MAX_ROUNDS,
            "checked_pages": [],
            "overflow_pages": {},
            "regenerated": {},
            "still_overflowing": {},
            "skipped": None,
        },
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
        logger.info(
            f"视觉质检环节开始：{total} 页，预算 {budget_seconds:.0f}s，"
            f"溢出硬关卡={'开' if gate_enabled else '关'}，VL 检查={'开' if vl_enabled else '关'}，"
            f"VISION_API_KEY={'已加载' if getattr(settings, 'VISION_API_KEY', '') else '未配置'}"
        )
        shots: List[Optional[bytes]] = [None] * total

        # ---- 相 A：溢出硬关卡（独立于 VISION_API_KEY / VL 开关）----
        if not gate_enabled:
            logger.info("溢出硬关卡跳过：OVERFLOW_GATE_ENABLED=false")
            summary["overflow"]["skipped"] = "OVERFLOW_GATE_ENABLED=false"
        else:
            gate_shots, overflows, gate_err = _screenshot_pages([make_doc(pg) for pg in pages], deadline)
            if gate_err:
                logger.error(
                    f"溢出硬关卡未执行：{gate_err}（chromium 为部署硬依赖："
                    "pip install playwright && playwright install chromium，且需中文字体）"
                )
                summary["overflow"]["skipped"] = gate_err
            else:
                shots = gate_shots
                logger.info(f"溢出硬关卡：截图测量 {total} 页")
                summary["overflow"]["checked_pages"] = [i + 1 for i in range(total) if overflows[i] is not None]
                for i in range(total):
                    px = overflows[i]
                    if px is None or px <= OVERFLOW_PX_THRESHOLD:
                        continue
                    pct = _overflow_pct(px)
                    summary["overflow"]["overflow_pages"][str(i + 1)] = pct
                    rounds = 0
                    while rounds < OVERFLOW_MAX_ROUNDS and time.time() < deadline:
                        rounds += 1
                        _progress(f"溢出检测：第 {i + 1} 页内容超页约 {pct}%，正在精简重生成（第 {rounds} 轮）…")
                        try:
                            rewritten = regen_page(i, pages[i], [_overflow_problem(px)])
                        except Exception as e:
                            logger.warning(f"溢出硬关卡第 {i + 1} 页重生成异常（保留原稿）: {e}")
                            break
                        if rewritten is None:
                            break
                        re_shots, re_overflows, re_err = _screenshot_pages([make_doc(rewritten)], deadline)
                        if re_err or not re_overflows or re_overflows[0] is None:
                            break
                        pages[i] = rewritten
                        shots[i] = re_shots[0]
                        px = re_overflows[0]
                        if px <= OVERFLOW_PX_THRESHOLD:
                            break
                        pct = _overflow_pct(px)
                    if rounds > 0:
                        summary["overflow"]["regenerated"][str(i + 1)] = rounds
                        if time.time() >= deadline:
                            summary["deadline_hit"] = True
                    if px > OVERFLOW_PX_THRESHOLD:
                        summary["overflow"]["still_overflowing"][str(i + 1)] = _overflow_pct(px)
                logger.info(
                    f"溢出硬关卡结果：超页 {summary['overflow']['overflow_pages'] or '无'}，"
                    f"重生成轮次 {summary['overflow']['regenerated'] or '无'}，"
                    f"仍超（已保留并记录）{summary['overflow']['still_overflowing'] or '无'}"
                )

        # ---- 相 B：VL 多模态视觉检查 ----
        if not vl_enabled:
            logger.info("VL 视觉检查跳过：VISUAL_QC_ENABLED=false（溢出硬关卡独立运行）")
            summary["skipped"] = "VISUAL_QC_ENABLED=false（仅关 VL 检查，溢出硬关卡独立运行）"
            return pages, summary
        if not getattr(settings, "VISION_API_KEY", ""):
            logger.info("VL 视觉检查跳过：未配置 VISION_API_KEY（溢出硬关卡不受影响）")
            summary["skipped"] = "未配置 VISION_API_KEY（溢出硬关卡不受影响）"
            return pages, summary
        if all(s is None for s in shots):  # 相 A 未产出截图（关闭或失败）→ 为 VL 现补
            logger.info(f"VL 检查：相 A 无可用截图，补拍 {total} 页")
            shots, _, shot_err = _screenshot_pages([make_doc(pg) for pg in pages], deadline)
            if shot_err:
                summary["error"] = shot_err
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
            logger.info(f"VL 触发重生成：第 {i + 1} 页（{len(issues)} 处视觉问题）")
            _progress(f"视觉质检：第 {i + 1} 页发现 {len(issues)} 处视觉问题，正在重新生成…")
            try:
                rewritten = regen_page(i, pages[i], issues)
            except Exception as e:
                logger.warning(f"视觉质检第 {i + 1} 页重生成异常（保留原稿）: {e}")
                rewritten = None
            if rewritten is not None:
                pages[i] = rewritten
                summary["regenerated_pages"].append(i + 1)
        logger.info(
            f"VL 检查完成：已检 {len(summary['checked_pages'])} 页，"
            f"未检 {summary['unchecked_pages'] or '无'}，问题页 {summary['issue_pages'] or '无'}，"
            f"重生成 {summary['regenerated_pages'] or '无'}"
        )
        return pages, summary
    except Exception as e:
        logger.warning(f"视觉质检整体异常，跳过: {e}")
        summary["error"] = str(e)[:200]
        return pages, summary
