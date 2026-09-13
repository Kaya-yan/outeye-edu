"""G2 冒烟：术语悬停气泡（portal+fixed 根治容器 overflow 裁剪）与点击抽屉完整解读

桌面：hover 出气泡 → 点击术语进抽屉 → Esc 关闭
移动：无 hover，首点点按出气泡 → 点「查看完整解读」进抽屉
前置：frontend dev server 跑在 localhost:3000

注意：分析完成后页面有 S1 自动平滑滚动，滚动中术语会从指针下移走
（触发 pointerleave 关气泡、tap 的兼容 click 被抑制），交互前必须等滚动停稳。
"""
import json
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "http://localhost:3000"
OUT = Path(__file__).parent / "_term_shots"
OUT.mkdir(exist_ok=True)

TEXT = ("Reading academic texts requires students to process dense information "
        "efficiently and understand complex arguments across long sentences. "
        "Teachers should scaffold vocabulary and structure analysis.")

ANALYSIS = {
    "text_id": "smoke-g2",
    "title": "G2 术语冒烟",
    "text_level": "B2",
    "language": "en",
    "language_name": "英语",
    "vocabulary": {
        "total_words": 38, "unique_words": 30,
        "cefr_distribution": {"A1": 12, "A2": 8, "B1": 6, "B2": 5, "C1": 3, "C2": 2},
        "awl_count": 4, "awl_ratio": 0.105,
        "difficult_words": [{"word": "scaffold", "level": "C1", "count": 1, "in_awl": True}],
        "vocabulary_richness": 0.79,
    },
    "syntax": {
        "total_sentences": 2, "avg_sentence_length": 19,
        "max_sentence": {"preview": "Reading academic texts…", "word_count": 22, "index": 0},
        "long_sentences_count": 1, "very_long_sentences_count": 0,
        "flesch_reading_ease": 42.5,
    },
    "discourse": {
        "paragraph_count": 1, "connective_density": 2.6, "genre_hint": "说明文",
        "text_structure": "总-分结构",
    },
    "learner_gap": {
        "text_level": "B2", "student_level": "B1", "gap": "i+1",
        "gap_description": "课文略高于学生当前水平，位于理想挑战区间。",
    },
    "enhancement_tags": ["long_sentences_present"],
    "cultural_elements": [],
    "tag_details": {}, "wiki_tags": [], "rag_tags": [],
    "teaching_tips": ["长句建议做主谓骨架拆解练习。"],
    "analysis_duration": 0.3,
    "metric_glossary": {
        "AWL 占比": {
            "name": "AWL 学术词汇占比",
            "definition": "学术词汇表（Academic Word List）词汇占全文的比重。",
            "interpretation": "本篇为 10.5%，学术密度中等。",
            "teaching": "学术词可预教词根词缀，降低阅读阻力。",
        },
    },
}

USER = {"id": "u1", "email": "t@example.com", "full_name": "测试教师"}

fail = 0


def check(label, ok):
    global fail
    if not ok:
        fail += 1
    print(f"{'OK ' if ok else 'FAIL'} {label}")


def wait_scroll_settle(page, timeout_ms=8000):
    deadline = time.time() + timeout_ms / 1000
    last, stable = page.evaluate("window.scrollY"), 0
    while time.time() < deadline:
        page.wait_for_timeout(150)
        y = page.evaluate("window.scrollY")
        stable = stable + 1 if y == last else 0
        if stable >= 3:
            return True
        last = y
    return False


def run(page, mode):
    page.goto(BASE + "/", wait_until="load", timeout=30000)
    page.locator(".ProseMirror").first.fill(TEXT)
    page.get_by_role("button", name="开始分析").click()
    page.get_by_text("六维分析雷达").wait_for(timeout=10000)

    term = page.get_by_role("button", name="AWL 占比").first
    term.scroll_into_view_if_needed()
    wait_scroll_settle(page)

    if mode == "desktop":
        term.hover()
    else:
        term.tap()  # 触屏无 hover，首点出气泡
    bubble = page.locator('[data-term-tooltip="AWL 占比"]')
    check(f"[{mode}] 悬停/点按出气泡", bubble.is_visible())
    body = bubble.inner_text()
    check(f"[{mode}] 气泡含术语全称", "AWL 学术词汇占比" in body)
    check(f"[{mode}] 气泡含一句话解释", "学术词汇表" in body)
    check(f"[{mode}] 气泡含完整解读入口", "完整解读" in body)
    # overflow 场景：气泡经 portal 渲染在 body 下，须完整落在视口内而非被祖先裁剪
    box = bubble.bounding_box()
    vw = page.evaluate("window.innerWidth")
    vh = page.evaluate("window.innerHeight")
    in_vp = bool(box) and box["x"] >= 0 and box["y"] >= 0 \
        and box["x"] + box["width"] <= vw and box["y"] + box["height"] <= vh
    check(f"[{mode}] 气泡完整在视口内（不被容器裁剪）", in_vp)
    if not in_vp:
        print(f"    box={box} vw={vw} vh={vh}")
    page.screenshot(path=str(OUT / f"{mode}_bubble.png"))

    if mode == "desktop":
        term.click()  # hover 已开气泡，点击直接进抽屉
    else:
        bubble.get_by_text("点击查看完整解读").tap()
    drawer = page.get_by_role("dialog")
    try:
        drawer.wait_for(state="visible", timeout=5000)
        check(f"[{mode}] 点击打开完整解读抽屉", True)
    except Exception:
        check(f"[{mode}] 点击打开完整解读抽屉", False)
        return
    dbody = drawer.inner_text()
    check(f"[{mode}] 抽屉含是什么/本文解读", "是什么" in dbody and "本文解读" in dbody)
    page.screenshot(path=str(OUT / f"{mode}_drawer.png"))

    page.keyboard.press("Escape")
    page.wait_for_timeout(200)
    check(f"[{mode}] Esc 关闭抽屉", drawer.count() == 0 or not drawer.is_visible())


with sync_playwright() as p:
    browser = p.chromium.launch()
    for mode, vp in [("desktop", {"width": 1280, "height": 900}), ("mobile", {"width": 375, "height": 812})]:
        ctx = browser.new_context(viewport=vp, is_mobile=(mode == "mobile"), has_touch=(mode == "mobile"))
        ctx.add_cookies([{"name": "auth_token", "value": "stub-token", "url": BASE}])

        def stub(route):
            url = route.request.url
            if "/users/me" in url:
                body = USER
            elif "/analysis/whitebox" in url:
                body = ANALYSIS
            elif "/knowledge" in url or "/projects" in url or "/components" in url:
                body = []
            else:
                body = {}
            route.fulfill(status=200, content_type="application/json", body=json.dumps(body, ensure_ascii=False))

        ctx.route("**/api/v1/**", stub)
        page = ctx.new_page()
        page.on("pageerror", lambda e: print(f"[{mode}] PAGEERROR {e}"))
        page.goto(BASE + "/login", wait_until="load")
        page.evaluate(
            "([t, u]) => { localStorage.setItem('token', t); localStorage.setItem('user', u); }",
            ["stub-token", json.dumps(USER, ensure_ascii=False)],
        )
        try:
            run(page, mode)
        except Exception as e:
            fail += 1
            print(f"[{mode}] ERROR {e}")
            page.screenshot(path=str(OUT / f"{mode}_error.png"))
        ctx.close()
    browser.close()

print("FAILED" if fail else "ALL CLEAN")
sys.exit(1 if fail else 0)
