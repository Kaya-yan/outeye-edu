"""任务③b 代理级冒烟：真实 chromium 指针事件验证拖拽调序（插入线/提交/原位不提交/微动不误触）

前置：node --input-type=module -e "…buildPickAgentScript('smoke-ch')…" 已生成 scripts/_agent_smoke.js
运行：PYTHONIOENCODING=utf-8 python scripts/smoke_drag_agent.py
"""

import sys
from pathlib import Path

sys.path.insert(0, ".")

from playwright.sync_api import sync_playwright

AGENT = Path("scripts/_agent_smoke.js").read_text(encoding="utf-8")

HTML = (
    "<html><head><style>section{display:block;margin:0 0 24px 0;padding:10px}</style></head><body>"
    '<div id="stage">'
    '<section class="page" data-page="1" data-title="A"><div class="page-focus">'
    "<p>one</p><p>two</p><p>three</p></div></section>"
    '<section class="page" data-page="2" data-title="B"><div class="page-focus"><p>b</p></div></section>'
    '<section class="page" data-page="3" data-title="C"><div class="page-focus"><p>c</p></div></section>'
    "</div>"
    '<button id="nav-prev">p</button><button id="nav-next">n</button>'
    '<div id="page-indicator">1 / 3</div>'
    '<div id="row" style="display:flex;gap:8px;width:600px;padding:10px">'
    "<span>甲</span><span>乙</span><span>丙</span><span>丁</span></div>"
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


def commits(page):
    return page.evaluate("window.__commits")


def center(page, selector):
    box = page.locator(selector).bounding_box()
    return box["x"] + box["width"] / 2, box["y"] + box["height"] / 2


results: list = []


def check(name, cond):
    results.append((name, bool(cond)))
    print(("PASS" if cond else "FAIL"), name)


with sync_playwright() as p:
    b = p.chromium.launch()
    page = b.new_page(viewport={"width": 1280, "height": 900})
    page.set_content(HTML, wait_until="load")

    page.evaluate(
        "window.__commits=[];window.__picks=[];"
        "window.addEventListener('message',function(ev){var d=ev.data;"
        "if(!d||d.ve!==1||d.ch!=='smoke-ch')return;"
        "if(d.type==='ve:move:commit')window.__commits.push(d.payload);"
        "if(d.type==='ve:pick')window.__picks.push(d.payload);});"
    )
    page.evaluate(
        "window.postMessage({ve:1,ch:'smoke-ch',type:'ve:pick:set',payload:{enabled:true}},'*')"
    )
    page.wait_for_timeout(150)

    x1, y1 = center(page, '[data-page="1"]')
    page.mouse.move(x1, y1)
    page.mouse.down()
    page.mouse.move(x1 + 3, y1 + 3)
    page.mouse.up()
    page.wait_for_timeout(150)
    check("微动（<6px）不触发拖拽，点击选取仍有效", len(commits(page)) == 0 and page.evaluate("window.__picks.length") == 1)

    b3 = page.locator('[data-page="3"]').bounding_box()
    px3, py3 = b3["x"] + 5, b3["y"] + 5
    page.mouse.move(px3, py3)
    page.mouse.down()
    page.mouse.move(px3, py3 - 30, steps=3)
    page.mouse.move(x1, y1 - 60, steps=5)
    line_shown = page.evaluate(
        "(document.getElementById('ve-drag-line')||{style:{}}).style.display==='block'"
    )
    ghost_shown = page.evaluate(
        "(document.getElementById('ve-drag-ghost')||{style:{}}).style.display==='block'"
    )
    page.mouse.up()
    page.wait_for_timeout(150)
    cs = commits(page)
    check("拖拽期间显示插入线与拖拽框", line_shown and ghost_shown)
    check("拖拽提交 ve:move:commit（page3 → 同级第 0 位）", len(cs) == 1 and cs[0]["targetIndex"] == 0 and cs[0]["tag"] == "section")
    check("提交后拖拽 UI 已清理",
          page.evaluate("!document.getElementById('ve-drag-style')") and
          page.evaluate("(document.getElementById('ve-drag-line')||{style:{}}).style.display==='none'"))

    apply(page, [{"kind": "move", "selector": cs[0]["selector"], "moveId": "oe-mv-d1", "targetIndex": cs[0]["targetIndex"]}])
    check("宿主回放 move 补丁后顺序 [3,1,2]", page_order(page) == ["3", "1", "2"])
    check("被拖元素盖稳定锚点", page.evaluate(
        "!!document.querySelector('section.page[data-title=\"C\"][data-oe-id=\"oe-mv-d1\"]')"
    ))

    b1 = page.locator('[data-page="1"]').bounding_box()
    pa, pb = b1["x"] + 5, b1["y"] + 5
    page.mouse.move(pa, pb)
    page.mouse.down()
    page.mouse.move(pa, pb + 40, steps=4)
    page.mouse.up()
    page.wait_for_timeout(150)
    check("原位拖拽（落点=当前位次）不产生提交", len(commits(page)) == 1)

    xp, yp = center(page, '[data-page="1"] .page-focus p:nth-of-type(2)')
    xt, yt = center(page, '[data-page="1"] .page-focus p:nth-of-type(3)')
    page.mouse.move(xp, yp)
    page.mouse.down()
    page.mouse.move(xp, yp - 20, steps=3)
    page.mouse.move(xt, yt + 30, steps=5)
    page.mouse.up()
    page.wait_for_timeout(150)
    cs2 = commits(page)
    check("页内段落拖到末尾（targetIndex=2）", len(cs2) == 2 and cs2[1]["targetIndex"] == 2 and cs2[1]["tag"] == "p")
    apply(page, [
        {"kind": "move", "selector": cs[0]["selector"], "moveId": "oe-mv-d1", "targetIndex": 0},
        {"kind": "move", "selector": cs2[1]["selector"], "moveId": "oe-mv-d2", "targetIndex": 2},
    ])
    check("回放后页内顺序 [one,three,two]", inner_texts(page) == ["one", "three", "two"])
    check("页级顺序不受页内拖拽影响", page_order(page) == ["3", "1", "2"])

    xp, yp = center(page, '[data-page="1"] .page-focus p:nth-of-type(2)')
    page.mouse.move(xp, yp)
    page.mouse.down()
    page.mouse.move(xp, yp - 20, steps=3)
    page.keyboard.press("Escape")
    page.mouse.up()
    page.wait_for_timeout(150)
    check("Esc 取消拖拽不提交", len(commits(page)) == 2)

    xj, yj = center(page, "#row span:nth-of-type(1)")
    xd, yd = center(page, "#row span:nth-of-type(4)")
    page.mouse.move(xd, yd)
    page.mouse.down()
    page.mouse.move(xd - 30, yd, steps=3)
    page.mouse.move(xj - 10, yj, steps=5)
    vline = page.evaluate(
        "(document.getElementById('ve-drag-line')||{style:{}}).style.width==='3px'"
    )
    page.mouse.up()
    page.wait_for_timeout(150)
    cs3 = commits(page)
    check("横向同行拖拽（插入线为竖线）", vline and len(cs3) == 3 and cs3[2]["targetIndex"] == 0 and cs3[2]["tag"] == "span")
    apply(page, [
        {"kind": "move", "selector": cs[0]["selector"], "moveId": "oe-mv-d1", "targetIndex": 0},
        {"kind": "move", "selector": cs2[1]["selector"], "moveId": "oe-mv-d2", "targetIndex": 2},
        {"kind": "move", "selector": cs3[2]["selector"], "moveId": "oe-mv-d3", "targetIndex": 0},
    ])
    check("回放后横向顺序 [丁,甲,乙,丙]", page.evaluate(
        "[].slice.call(document.querySelectorAll('#row span')).map(s=>s.textContent)"
    ) == ["丁", "甲", "乙", "丙"])

    b.close()

fails = [n for n, ok in results if not ok]
print("\n冒烟结论:", "FAIL — " + "; ".join(fails) if fails else f"PASS（{len(results)} 项）")
sys.exit(1 if fails else 0)
