"""S6 视觉质检闭环（两相）：溢出硬关卡（本地几何）+ VL 多模态检查

相 A 溢出硬关卡（OVERFLOW_GATE_ENABLED，默认开，纯本地零外部依赖，geo-v2）：
截图环节在 chromium 内做三级确定性测量——
1) 页级溢出：section.page 的 scrollHeight - clientHeight（overflow:hidden 下
   scrollHeight 仍报告被裁内容全高）；
2) 组件内裁剪：遍历 overflow:hidden / line-clamp 元素，scroll 尺寸超出阈值即内容被裁；
3) 兄弟重叠：page-focus 直接子元素（排除绝对定位装饰）两两比对包围盒，交叠面积占
   较小盒比例超阈值即叠压遮挡。
违规页带组件级定位反馈（如「词汇卡 第2张…内容超出容器约 30px」）重生成，每页最多
2 轮，仍违规则保留并记录（页级进 still_overflowing、元素级进 still_element_issues，
经 generator 落入 overflow_notices 给前端教师提示）。chromium/playwright 不可用时
ERROR 级日志 + summary 记录（chromium 是部署硬依赖，不做静态估算兜底，诚实可见）。

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
ELEMENT_CLIP_PX_THRESHOLD = 12
OVERLAP_AREA_RATIO = 0.05

# 元素级测量的浏览器端脚本（任务D 检测升级：页级溢出 + 组件内裁剪 + 兄弟重叠）
_MEASURE_JS = """e => {
  const out = { over: e.scrollHeight - e.clientHeight, clips: [], overlaps: [] };
  const CN = {
    'vocab-card': '词汇卡', 'front': '卡正面', 'back': '卡背面', 'timeline': '时间线',
    'timer': '计时器', 'reveal': '折叠问答', 'mark-words': '点击标词', 'fill-blanks': '语境填空',
    'sort-paragraphs': '段落排序', 'para-original': '原文段落卡', 'para-gist': '段落主旨',
    'sentence-anatomy': '长难句解剖', 'lang-points': '语言点', 'cohesion-note': '衔接点评',
    'sent-walk': '逐句细读', 'anatomy-sentence': '解剖句', 'anatomy-legend': '成分图例',
    'page-focus': '焦点容器', 'card': '卡片', 'callout': '强调框',
  };
  const STATE = /^(lit|flip|picked|hit|miss|shake|dragging|open|x-ray)$/;
  function desc(el) {
    const classes = (el.getAttribute('class') || '').split(/\\s+/).filter(c => c && !STATE.test(c));
    const cls = classes[0] || '';
    let base = (cls && CN[cls]) || cls || el.tagName.toLowerCase();
    if (cls) {
      const sibs = [].slice.call(el.parentNode.children).filter(k => {
        const kc = (k.getAttribute('class') || '').split(/\\s+/);
        return k.tagName === el.tagName && kc.indexOf(cls) >= 0;
      });
      if (sibs.length > 1) base += ' 第' + (sibs.indexOf(el) + 1) + '张/共' + sibs.length + '张';
    }
    const t = (el.innerText || '').replace(/\\s+/g, '').slice(0, 8);
    return t ? base + '（' + t + '…）' : base;
  }
  // a) 组件内裁剪：overflow hidden / line-clamp 元素，scroll 尺寸超出即内容被裁
  const CLIP = %CLIP_PX%;
  for (const c of e.querySelectorAll('*')) {
    const cs = getComputedStyle(c);
    const lc = cs.webkitLineClamp;
    const clamped = lc && lc !== 'none' && parseInt(lc, 10) > 0;
    const hidden = cs.overflow === 'hidden' || cs.overflowY === 'hidden' || cs.overflowX === 'hidden';
    if (!hidden && !clamped) continue;
    const dh = c.scrollHeight - c.clientHeight;
    const dw = c.scrollWidth - c.clientWidth;
    const px = Math.max(dh, dw);
    if (px > CLIP) out.clips.push({ desc: desc(c), px: Math.round(px) });
  }
  // b) 兄弟重叠：page-focus 直接子元素（排除绝对定位装饰），交叠面积占小盒比例超阈值
  const host = e.querySelector('.page-focus') || e;
  const kids = [].slice.call(host.children).filter(k => {
    const r = k.getBoundingClientRect();
    if (r.width < 2 || r.height < 2) return false;
    const p = getComputedStyle(k).position;
    return p !== 'absolute' && p !== 'fixed';
  });
  for (let i = 0; i < kids.length; i++) {
    for (let j = i + 1; j < kids.length; j++) {
      const a = kids[i].getBoundingClientRect(), b = kids[j].getBoundingClientRect();
      const ix = Math.min(a.right, b.right) - Math.max(a.left, b.left);
      const iy = Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top);
      if (ix <= 2 || iy <= 2) continue;
      const smaller = Math.min(a.width * a.height, b.width * b.height) || 1;
      const pct = Math.round(ix * iy / smaller * 100);
      if (pct > %OVERLAP_PCT%) out.overlaps.push({ a: desc(kids[i]), b: desc(kids[j]), pct });
    }
  }
  return out;
}"""


def _measure_js() -> str:
    return (
        _MEASURE_JS
        .replace("%CLIP_PX%", str(ELEMENT_CLIP_PX_THRESHOLD))
        .replace("%OVERLAP_PCT%", str(round(OVERLAP_AREA_RATIO * 100)))
    )


def _screenshot_pages_real(docs: List[str], deadline: float) -> Tuple[List[Optional[bytes]], List[Optional[Any]], Optional[str]]:
    """串行逐页截图+元素级测量：每份单页文档渲染后对 section.page 截图（jpeg q70），
    并量页级溢出 + 组件内裁剪 + 兄弟重叠（返回 dict）；失败返回错误串。"""
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
                overflows: List[Optional[Any]] = []
                for doc in docs:
                    if time.time() >= deadline:
                        shots.append(None)
                        overflows.append(None)
                        continue
                    ctx.set_content(doc, wait_until="load")
                    el = ctx.locator("section.page").first
                    shots.append(el.screenshot(type="jpeg", quality=70))
                    overflows.append(el.evaluate(_measure_js()))
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


def _page_over(v: Optional[Any]) -> Optional[int]:
    """归一化测量值：新格式 dict 取页级溢出，旧格式/测试 mock 直接是 int"""
    if v is None:
        return None
    if isinstance(v, dict):
        return v.get("over")
    return v


def _element_problems(v: Optional[Any]) -> List[str]:
    """元素级违规反馈：组件内裁剪 + 兄弟重叠，带组件级定位（如"词汇卡 第2张…超约 30px"）"""
    if not isinstance(v, dict):
        return []
    problems: List[str] = []
    for c in v.get("clips") or []:
        problems.append(
            f"「{c.get('desc') or '组件'}」内容超出容器约 {c.get('px', 0)}px 被裁剪不可见，"
            "请精简该组件内容（释义/例句/描述控制在预算行数内，或减少该组件数量）"
        )
    for o in v.get("overlaps") or []:
        problems.append(
            f"「{o.get('a') or '元素'}」与「{o.get('b') or '元素'}」位置交叠约 {o.get('pct', 0)}%，内容互相遮挡，"
            "请精简上方内容、减少条目或缩短文本，消除叠压"
        )
    return problems


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
            "gate_version": "geo-v2",
            "threshold_px": OVERFLOW_PX_THRESHOLD,
            "element_clip_threshold_px": ELEMENT_CLIP_PX_THRESHOLD,
            "overlap_area_ratio": OVERLAP_AREA_RATIO,
            "max_rounds": OVERFLOW_MAX_ROUNDS,
            "checked_pages": [],
            "overflow_pages": {},
            "regenerated": {},
            "still_overflowing": {},
            "still_element_issues": {},
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
                logger.info(f"溢出硬关卡：截图测量 {total} 页（页级溢出 + 组件内裁剪 + 兄弟重叠）")
                summary["overflow"]["checked_pages"] = [i + 1 for i in range(total) if overflows[i] is not None]
                for i in range(total):
                    px = _page_over(overflows[i])
                    elem_probs = _element_problems(overflows[i])
                    page_bad = px is not None and px > OVERFLOW_PX_THRESHOLD
                    if not page_bad and not elem_probs:
                        continue
                    if page_bad:
                        summary["overflow"]["overflow_pages"][str(i + 1)] = _overflow_pct(px)
                    rounds = 0
                    while rounds < OVERFLOW_MAX_ROUNDS and time.time() < deadline:
                        rounds += 1
                        problems = ([_overflow_problem(px)] if page_bad else []) + elem_probs
                        head = (
                            f"溢出检测：第 {i + 1} 页内容超页约 {_overflow_pct(px)}%"
                            + (f"，另有 {len(elem_probs)} 处组件遮挡" if elem_probs else "")
                            if page_bad
                            else f"遮挡检测：第 {i + 1} 页存在 {len(elem_probs)} 处组件遮挡问题"
                        )
                        _progress(f"{head}，正在精简重生成（第 {rounds} 轮）…")
                        try:
                            rewritten = regen_page(i, pages[i], problems)
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
                        px = _page_over(re_overflows[0])
                        elem_probs = _element_problems(re_overflows[0])
                        page_bad = px is not None and px > OVERFLOW_PX_THRESHOLD
                        if not page_bad and not elem_probs:
                            break
                    if rounds > 0:
                        summary["overflow"]["regenerated"][str(i + 1)] = rounds
                        if time.time() >= deadline:
                            summary["deadline_hit"] = True
                    if page_bad:
                        summary["overflow"]["still_overflowing"][str(i + 1)] = _overflow_pct(px)
                    if elem_probs:
                        summary["overflow"]["still_element_issues"][str(i + 1)] = elem_probs
                logger.info(
                    f"溢出硬关卡结果：超页 {summary['overflow']['overflow_pages'] or '无'}，"
                    f"重生成轮次 {summary['overflow']['regenerated'] or '无'}，"
                    f"仍超（已保留并记录）{summary['overflow']['still_overflowing'] or '无'}，"
                    f"元素级仍违规 {summary['overflow']['still_element_issues'] or '无'}"
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
