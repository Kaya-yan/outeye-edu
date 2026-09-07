"""任务③a 代理级冒烟：真实 chromium DOM 验证 move 补丁（重放/幂等/同级约束/导出重编号）

前置：node --input-type=module -e "…buildPickAgentScript('smoke-ch')…" 已生成 scripts/_agent_smoke.js
运行：PYTHONIOENCODING=utf-8 python scripts/smoke_move_agent.py
"""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, ".")

from playwright.sync_api import sync_playwright

AGENT = Path("scripts/_agent_smoke.js").read_text(encoding="utf-8")

HTML = (
    "<html><head><style>section{display:block}</style></head><body>"
    '<div id="stage">'
    '<section class="page" data-page="1" data-title="A"><div class="page-focus">'
    "<p>one</p><p>two</p><p>three</p></div></section>"
    '<section class="page" data-page="2" data-title="B"><div class="page-focus"><p>b</p></div></section>'
    '<section class="page" data-page="3" data-title="C"><div class="page-focus"><p>c</p></div></section>'
    "</div>"
    '<button id="nav-prev">p</button><button id="nav-next">n</button>'
    '<div id="page-indicator">1 / 3</div>'
    "<script>" + AGENT + "</script>"
    "</body></html>"
)


def apply(page, patches):
    page.evaluate(
        "p => window.postMessage({ve:1,ch:'smoke-ch',type:'ve:patches:applyAll',payload:{css:'',patches:p}},'*')",
        patches,
    )
    page.wait_for_timeout(150)


def page_order(page):
    return page.evaluate(
        "[].slice.call(document.querySelectorAll('section.page')).map(s=>s.getAttribute('data-page'))"
    )


def inner_texts(page):
    return page.evaluate(
        "[].slice.call(document.querySelectorAll('[data-page=\"1\"] .page-focus p')).map(p=>p.textContent)"
    )


results: list = []


def check(name, cond):
    results.append((name, bool(cond)))
    print(("PASS" if cond else "FAIL"), name)


with sync_playwright() as p:
    b = p.chromium.launch()
    page = b.new_page()
    page.set_content(HTML, wait_until="load")

    move_page3 = {"kind": "move", "selector": '[data-page="3"]', "moveId": "oe-mv-1", "targetIndex": 0}
    apply(page, [move_page3])
    check("页面级上移：3 移到最前", page_order(page) == ["3", "1", "2"])
    check("被移动页获得稳定锚点", page.evaluate(
        "!!document.querySelector('section.page[data-title=\"C\"][data-oe-id=\"oe-mv-1\"]')"
    ))
    check("移动未波及导航按钮位置", page.evaluate(
        "document.getElementById('stage').lastElementChild.tagName === 'SECTION'"
    ))

    apply(page, [dict(move_page3, targetIndex=2)])
    check("页面级下移（补丁更新后重放）", page_order(page) == ["1", "2", "3"])

    apply(page, [dict(move_page3, targetIndex=0), dict(move_page3, targetIndex=0)])
    check("重放幂等", page_order(page) == ["3", "1", "2"])

    move_p2 = {"kind": "move", "selector": '[data-page="1"] .page-focus p:nth-of-type(2)',
               "moveId": "oe-mv-2", "targetIndex": 2}
    apply(page, [dict(move_page3, targetIndex=0), move_p2])
    check("页内同级下移（跨页不生效语义：仅在同级内）", inner_texts(page) == ["one", "three", "two"])

    exported_html = page.evaluate(
        "() => new Promise(res => {"
        "window.addEventListener('message', function h(ev){"
        "if(ev.data&&ev.data.ve===1&&ev.data.type==='ve:export:result'){"
        "window.removeEventListener('message',h);res(ev.data.payload.html);}});"
        "window.postMessage({ve:1,ch:'smoke-ch',type:'ve:export',payload:{css:''}},'*');})"
    )
    pairs = re.findall(r'data-page="(\d+)" data-title="([ABC])"', exported_html)
    check("导出重编号 data-page（DOM 顺序 1..N）", pairs == [("1", "C"), ("2", "A"), ("3", "B")])
    check("导出保留稳定锚点", 'data-oe-id="oe-mv-1"' in exported_html)

    apply(page, [])
    order_after_clear = page_order(page)
    check("清空补丁后位置保留（与 text 补丁同语义，撤销靠历史快照）", order_after_clear == ["3", "1", "2"])

    b.close()

fails = [n for n, ok in results if not ok]
print("\n冒烟结论:", "FAIL — " + "; ".join(fails) if fails else f"PASS（{len(results)} 项）")
sys.exit(1 if fails else 0)
