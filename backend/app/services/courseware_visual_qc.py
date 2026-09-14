"""S6 视觉质检闭环（两相）：遮挡硬关卡（本地几何 geo-v3）+ VL 多模态检查

章节式滚动课件（2026-09-11 格式转向）：无页高概念，删页级溢出检测，保留并加深两级：
1) 组件内裁剪：遍历 overflow:hidden / line-clamp 元素（折叠组件收起态除外），
   scroll 尺寸超出阈值即内容被裁；
2) 兄弟重叠全树检测：从节根向下遍历每个容器，对容器内子元素两两比对包围盒
   （排除绝对/固定定位、inline、零尺寸），交叠面积占较小盒比例超阈值即叠压遮挡
   ——全树深度覆盖双栏文字互相穿插类漏检（P25）。
违规节带组件级定位反馈（如「词汇卡 第2张…内容超出容器约 30px」）重生成，每节最多
2 轮，仍违规则保留并记录（进 still_element_issues，经 generator 落入
overflow_notices 给前端教师提示）。chromium/playwright 不可用时 ERROR 级日志 +
summary 记录（chromium 是部署硬依赖，不做静态估算兜底，诚实可见）。

相 B VL 视觉检查（VISUAL_QC_ENABLED 门控 + VISION_API_KEY 必需）：
DashScope Qwen-VL 并发 2 查可见视觉缺陷（文字重叠/版式塌陷/对比度）→ 有缺陷的
节重生成一轮（带缺陷清单）。截图目标 .oe-section（新骨架）优先、section.page
（旧分页骨架）回退；截图前给 body 加 oe-no-anim 关闭滚动动效保证确定性。

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

VISUAL_QC_PROMPT_NAME = "courseware_visual_qc_v2"
VISUAL_BUDGET_SECONDS = 240.0
VL_CONCURRENCY = 2

OVERFLOW_MAX_ROUNDS = 2
ELEMENT_CLIP_PX_THRESHOLD = 12
OVERLAP_AREA_RATIO = 0.05
MAX_PROBLEMS_PER_PAGE = 6
SHOT_MAX_HEIGHT = 2000

# 元素级测量的浏览器端脚本（geo-v3：组件内裁剪 + 全树兄弟重叠 + 浮动层越界；无页高概念）
# 浮动层（[data-float]，编辑器浮动补丁产物）：absolute 定位已不参与兄弟重叠检测
# （浮 vs 浮 / 浮 vs 正文叠压属有意设计，豁免），仅检查是否超出所属节边界。
_MEASURE_JS = """e => {
  const out = { clips: [], overlaps: [], floats: [] };
  const CN = {
    'vocab-card': '词汇卡', 'front': '卡正面', 'back': '卡背面', 'timeline': '时间线',
    'timer': '计时器', 'reveal': '折叠问答', 'mark-words': '点击标词', 'fill-blanks': '语境填空',
    'sort-paragraphs': '段落排序', 'para-original': '原文段落卡', 'para-gist': '段落主旨',
    'sentence-anatomy': '长难句解剖', 'lang-points': '语言点', 'cohesion-note': '衔接点评',
    'sent-walk': '逐句细读', 'anatomy-sentence': '解剖句', 'anatomy-legend': '成分图例',
    'page-focus': '焦点容器', 'card': '卡片', 'callout': '强调框',
    'oe-section': '节', 'oe-chapter': '章', 'ch-head': '章头', 'vocab-grid': '词卡组',
    'ix-actions': '练习按钮区', 'mw-text': '标词正文', 'fb-text': '填空正文', 'sp-list': '排序卡列表',
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
  //    （滚动骨架版心与折叠组件收起态之外的 overflow:hidden 属裁内容违规）
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
  // b) 兄弟重叠全树检测：每个容器的子元素两两比对（排除绝对/固定定位、inline、零尺寸）
  const seen = {};
  const pairKey = (a, b, pct) => a + '\\u0001' + b + '\\u0001' + pct;
  function measurableKids(node) {
    return [].slice.call(node.children).filter(k => {
      const r = k.getBoundingClientRect();
      if (r.width < 2 || r.height < 2) return false;
      const cs = getComputedStyle(k);
      if (cs.position === 'absolute' || cs.position === 'fixed') return false;
      if (cs.display === 'inline') return false;
      return cs.visibility !== 'hidden';
    });
  }
  function walk(node) {
    const kids = measurableKids(node);
    for (let i = 0; i < kids.length; i++) {
      for (let j = i + 1; j < kids.length; j++) {
        const a = kids[i].getBoundingClientRect(), b = kids[j].getBoundingClientRect();
        const ix = Math.min(a.right, b.right) - Math.max(a.left, b.left);
        const iy = Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top);
        if (ix <= 2 || iy <= 2) continue;
        const smaller = Math.min(a.width * a.height, b.width * b.height) || 1;
        const pct = Math.round(ix * iy / smaller * 100);
        if (pct <= %OVERLAP_PCT%) continue;
        const da = desc(kids[i]), db = desc(kids[j]);
        const key = pairKey(da, db, pct);
        if (seen[key]) continue;
        seen[key] = 1;
        out.overlaps.push({ a: da, b: db, pct });
      }
    }
    for (const k of kids) walk(k);
  }
  walk(e);
  // c) 浮动层越界：只查不越界（允许压住正文），须完整落在所属节内
  for (const f of e.querySelectorAll('[data-float]')) {
    const sec = f.closest ? f.closest('.oe-section, section.page') : null;
    if (!sec) { out.floats.push({ desc: desc(f), issue: '未锚定到任何节' }); continue; }
    const fr = f.getBoundingClientRect(), sr = sec.getBoundingClientRect();
    const TOL = 2;
    const over = [];
    if (fr.left < sr.left - TOL) over.push('左' + Math.round(sr.left - fr.left) + 'px');
    if (fr.right > sr.right + TOL) over.push('右' + Math.round(fr.right - sr.right) + 'px');
    if (fr.top < sr.top - TOL) over.push('上' + Math.round(sr.top - fr.top) + 'px');
    if (fr.bottom > sr.bottom + TOL) over.push('下' + Math.round(fr.bottom - sr.bottom) + 'px');
    if (over.length) out.floats.push({ desc: desc(f), issue: '越界：' + over.join('、') });
  }
  if (out.clips.length > %MAX_PROBS%) out.clips.length = %MAX_PROBS%;
  if (out.overlaps.length > %MAX_PROBS%) out.overlaps.length = %MAX_PROBS%;
  if (out.floats.length > %MAX_PROBS%) out.floats.length = %MAX_PROBS%;
  return out;
}"""


def _measure_js() -> str:
    return (
        _MEASURE_JS
        .replace("%CLIP_PX%", str(ELEMENT_CLIP_PX_THRESHOLD))
        .replace("%OVERLAP_PCT%", str(round(OVERLAP_AREA_RATIO * 100)))
        .replace("%MAX_PROBS%", str(MAX_PROBLEMS_PER_PAGE))
    )


def _screenshot_pages_real(docs: List[str], deadline: float) -> Tuple[List[Optional[bytes]], List[Optional[Any]], Optional[str]]:
    """串行逐节截图+元素级测量：每份单节文档渲染后截 .oe-section（旧骨架回退
    section.page，jpeg q70、超高节截顶部 SHOT_MAX_HEIGHT），并量组件内裁剪 +
    全树兄弟重叠（返回 dict）；失败返回错误串。截图前给 body 加 oe-no-anim
    关闭淡入动效，保证测量与截图确定性。"""
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
                    try:
                        ctx.evaluate("() => { if (document.body) document.body.classList.add('oe-no-anim'); }")
                    except Exception:
                        pass
                    el = ctx.locator(".oe-section").first
                    if el.count() == 0:
                        el = ctx.locator("section.page").first
                    bb = el.bounding_box()
                    if bb and bb["height"] > SHOT_MAX_HEIGHT:
                        shots.append(ctx.screenshot(
                            type="jpeg", quality=70,
                            clip={"x": bb["x"], "y": bb["y"], "width": bb["width"], "height": SHOT_MAX_HEIGHT},
                        ))
                    else:
                        shots.append(el.screenshot(type="jpeg", quality=70))
                    overflows.append(el.evaluate(_measure_js()))
            finally:
                browser.close()
        return shots, overflows, None
    except Exception as e:
        return [], [], f"chromium 截图失败: {e}"


_screenshot_pages = _screenshot_pages_real


def _vl_check_real(shot: bytes, prompt: str) -> Optional[List[str]]:
    """DashScope Qwen-VL 单节视觉检查；失败返回 None（该节记未检）"""
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
    for fl in v.get("floats") or []:
        problems.append(
            f"「{fl.get('desc') or '浮动元素'}」{fl.get('issue') or '超出所属节'}，"
            "请在编辑器中拖回节内（浮动元素允许压住正文，但不可超出所属节边界）"
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
    """视觉质检入口（两相）：返回（可能被重生成的节列表, 摘要）；任何异常降级不阻塞"""

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
            "gate_version": "geo-v3",
            "element_clip_threshold_px": ELEMENT_CLIP_PX_THRESHOLD,
            "overlap_area_ratio": OVERLAP_AREA_RATIO,
            "max_rounds": OVERFLOW_MAX_ROUNDS,
            "checked_pages": [],
            "regenerated": {},
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
            f"视觉质检环节开始：{total} 节，预算 {budget_seconds:.0f}s，"
            f"遮挡硬关卡={'开' if gate_enabled else '关'}，VL 检查={'开' if vl_enabled else '关'}，"
            f"VISION_API_KEY={'已加载' if getattr(settings, 'VISION_API_KEY', '') else '未配置'}"
        )
        shots: List[Optional[bytes]] = [None] * total

        # ---- 相 A：遮挡硬关卡（独立于 VISION_API_KEY / VL 开关）----
        if not gate_enabled:
            logger.info("遮挡硬关卡跳过：OVERFLOW_GATE_ENABLED=false")
            summary["overflow"]["skipped"] = "OVERFLOW_GATE_ENABLED=false"
        else:
            gate_shots, measurements, gate_err = _screenshot_pages([make_doc(pg) for pg in pages], deadline)
            if gate_err:
                logger.error(
                    f"遮挡硬关卡未执行：{gate_err}（chromium 为部署硬依赖："
                    "pip install playwright && playwright install chromium，且需中文字体）"
                )
                summary["overflow"]["skipped"] = gate_err
            else:
                shots = gate_shots
                logger.info(f"遮挡硬关卡：截图测量 {total} 节（组件内裁剪 + 全树兄弟重叠）")
                summary["overflow"]["checked_pages"] = [i + 1 for i in range(total) if measurements[i] is not None]
                for i in range(total):
                    elem_probs = _element_problems(measurements[i])
                    if not elem_probs:
                        continue
                    rounds = 0
                    while rounds < OVERFLOW_MAX_ROUNDS and time.time() < deadline:
                        rounds += 1
                        _progress(
                            f"遮挡检测：第 {i + 1} 节存在 {len(elem_probs)} 处组件遮挡问题，"
                            f"正在精简重生成（第 {rounds} 轮）…"
                        )
                        try:
                            rewritten = regen_page(i, pages[i], elem_probs)
                        except Exception as e:
                            logger.warning(f"遮挡硬关卡第 {i + 1} 节重生成异常（保留原稿）: {e}")
                            break
                        if rewritten is None:
                            break
                        re_shots, re_measure, re_err = _screenshot_pages([make_doc(rewritten)], deadline)
                        if re_err or not re_measure or re_measure[0] is None:
                            break
                        pages[i] = rewritten
                        shots[i] = re_shots[0]
                        elem_probs = _element_problems(re_measure[0])
                        if not elem_probs:
                            break
                    if rounds > 0:
                        summary["overflow"]["regenerated"][str(i + 1)] = rounds
                        if time.time() >= deadline:
                            summary["deadline_hit"] = True
                    if elem_probs:
                        summary["overflow"]["still_element_issues"][str(i + 1)] = elem_probs
                logger.info(
                    f"遮挡硬关卡结果：重生成轮次 {summary['overflow']['regenerated'] or '无'}，"
                    f"元素级仍违规（已保留并记录）{summary['overflow']['still_element_issues'] or '无'}"
                )

        # ---- 相 B：VL 多模态视觉检查 ----
        if not vl_enabled:
            logger.info("VL 视觉检查跳过：VISUAL_QC_ENABLED=false（遮挡硬关卡独立运行）")
            summary["skipped"] = "VISUAL_QC_ENABLED=false（仅关 VL 检查，遮挡硬关卡独立运行）"
            return pages, summary
        if not getattr(settings, "VISION_API_KEY", ""):
            logger.info("VL 视觉检查跳过：未配置 VISION_API_KEY（遮挡硬关卡不受影响）")
            summary["skipped"] = "未配置 VISION_API_KEY（遮挡硬关卡不受影响）"
            return pages, summary
        if all(s is None for s in shots):  # 相 A 未产出截图（关闭或失败）→ 为 VL 现补
            logger.info(f"VL 检查：相 A 无可用截图，补拍 {total} 节")
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
                logger.warning(f"视觉质检第 {i + 1} 节 VL 调用失败（记未检）: {e}")
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
            logger.info(f"VL 触发重生成：第 {i + 1} 节（{len(issues)} 处视觉问题）")
            _progress(f"视觉质检：第 {i + 1} 节发现 {len(issues)} 处视觉问题，正在重新生成…")
            try:
                rewritten = regen_page(i, pages[i], issues)
            except Exception as e:
                logger.warning(f"视觉质检第 {i + 1} 节重生成异常（保留原稿）: {e}")
                rewritten = None
            if rewritten is not None:
                pages[i] = rewritten
                summary["regenerated_pages"].append(i + 1)
        logger.info(
            f"VL 检查完成：已检 {len(summary['checked_pages'])} 节，"
            f"未检 {summary['unchecked_pages'] or '无'}，问题节 {summary['issue_pages'] or '无'}，"
            f"重生成 {summary['regenerated_pages'] or '无'}"
        )
        return pages, summary
    except Exception as e:
        logger.warning(f"视觉质检整体异常，跳过: {e}")
        summary["error"] = str(e)[:200]
        return pages, summary
