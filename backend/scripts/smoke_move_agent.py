"""任务C 代理级冒烟：真实 chromium DOM 验证 move 补丁与拖拽体验

场景一（承接任务③）：move 补丁重放/幂等/同级约束/导出重编号
场景二（任务C）：toPage 跨页移动补丁（重放到目标页 .page-focus 末尾 + 稳定锚点 + 幂等 + 导出）
场景三（任务C）：拖拽手柄可见性/幽灵预览跟随/元素半透明/ve:move:commit 提交

前置：node --input-type=module -e "…buildPickAgentScript('smoke-ch')…" 已生成 scripts/_agent_smoke.js
运行：PYTHONIOENCODING=utf-8 python scripts/smoke_move_agent.py
"""

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


def post(page, mtype, payload):
    page.evaluate(
        "([t,pl]) => window.postMessage({ve:1,ch:'smoke-ch',type:t,payload:pl},'*')",
        [mtype, payload],
    )
    page.wait_for_timeout(100)


def collect_msgs(page):
    page.evaluate(
        "window.__msgs=[];"
        "window.addEventListener('message',function(ev){"
        "if(ev.data&&ev.data.ve===1&&ev.data.ch==='smoke-ch')window.__msgs.push(ev.data);});"
    )


def last_msg(page, mtype):
    return page.evaluate("t=>{var m=window.__msgs.filter(x=>x.type===t);return m.length?m[m.length-1]:null;}", mtype)


def page_order(page):
    return page.evaluate(
        "[].slice.call(document.querySelectorAll('section.page')).map(s=>s.getAttribute('data-page'))"
    )


def focus_texts(page, pageNo):
    return page.evaluate(
        "n=>[].slice.call(document.querySelectorAll('section.page[data-page=\"'+n+'\"] .page-focus p')).map(p=>p.textContent)",
        pageNo,
    )


def export_html(page):
    return page.evaluate(
        "() => new Promise(res => {"
        "window.addEventListener('message', function h(ev){"
        "if(ev.data&&ev.data.ve===1&&ev.data.type==='ve:export:result'){"
        "window.removeEventListener('message',h);res(ev.data.payload.html);}});"
        "window.postMessage({ve:1,ch:'smoke-ch',type:'ve:export',payload:{css:''}},'*');})"
    )


results: list = []


def check(name, cond):
    results.append((name, bool(cond)))
    print(("PASS" if cond else "FAIL"), name)


with sync_playwright() as p:
    b = p.chromium.launch()

    # ---- 场景一：同级 move 补丁（承接任务③）----
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
    check("页内同级下移（跨页不生效语义：仅在同级内）", focus_texts(page, "1") == ["one", "three", "two"])

    exported = export_html(page)
    pairs = re.findall(r'data-page="(\d+)" data-title="([ABC])"', exported)
    check("导出重编号 data-page（DOM 顺序 1..N）", pairs == [("1", "C"), ("2", "A"), ("3", "B")])
    check("导出保留稳定锚点", 'data-oe-id="oe-mv-1"' in exported)

    apply(page, [])
    check("清空补丁后位置保留（与 text 补丁同语义，撤销靠历史快照）", page_order(page) == ["3", "1", "2"])
    page.close()

    # ---- 场景二：任务C toPage 跨页移动补丁 ----
    page = b.new_page()
    page.set_content(HTML, wait_until="load")

    move_to_p2 = {"kind": "move", "selector": '[data-page="1"] .page-focus p:nth-of-type(1)',
                  "moveId": "oe-mv-9", "toPage": 2}
    apply(page, [move_to_p2])
    check("跨页移动：源页只剩 two/three", focus_texts(page, "1") == ["two", "three"])
    check("跨页移动：落到目标页 .page-focus 末尾", focus_texts(page, "2") == ["b", "one"])
    check("跨页移动元素获得稳定锚点", page.evaluate(
        "!!document.querySelector('section.page[data-page=\"2\"] .page-focus p[data-oe-id=\"oe-mv-9\"]')"
    ))

    apply(page, [move_to_p2])
    check("跨页移动重放幂等（不重复搬移）", focus_texts(page, "2") == ["b", "one"])

    exported = export_html(page)
    check("导出保留跨页结果（b 后接 one 且带锚点）",
          bool(re.search(r'<p>b</p><p data-oe-id="oe-mv-9">one</p>', exported)))
    page.close()

    # ---- 场景三：任务C 拖拽手柄 + 幽灵预览 + ve:move:commit ----
    page = b.new_page()
    page.set_content(HTML, wait_until="load")
    collect_msgs(page)

    post(page, "ve:pick:set", {"enabled": True})
    check("开启拾取模式回执", (last_msg(page, "ve:pick:mode") or {}).get("payload", {}).get("enabled") is True)
    check("未选中元素时手柄隐藏", page.evaluate(
        "var h=document.getElementById('ve-drag-handle');!h||h.style.display==='none'"
    ))

    first_p = page.locator('[data-page="1"] .page-focus p').first
    pr = first_p.bounding_box()
    first_p.click()
    page.wait_for_timeout(100)
    picked = last_msg(page, "ve:pick")
    check("点击元素发出 ve:pick", picked is not None)
    h = page.locator("#ve-drag-handle")
    hr = h.bounding_box()
    check("选中后手柄显示在元素左上", hr is not None and abs(hr["x"] - pr["x"]) < 2 and hr["y"] <= pr["y"])

    hx, hy = hr["x"] + hr["width"] / 2, hr["y"] + hr["height"] / 2
    x2, y2 = hx + 30, hy + 50
    page.mouse.move(hx, hy)
    page.mouse.down()
    page.mouse.move(x2, y2, steps=5)
    page.wait_for_timeout(100)
    ghost = page.evaluate(
        "()=>{var g=document.getElementById('ve-drag-ghost');var r=g.getBoundingClientRect();"
        "return {d:g.style.display,l:Math.round(r.left),t:Math.round(r.top),w:Math.round(r.width)};}"
    )
    # 鼠标远离视口边缘，clamp 不触发，幽灵应恰好右下偏移 14px
    check("拖拽中幽灵显示并跟随光标（右下偏移 14px）",
          ghost["d"] == "flex" and ghost["l"] == round(x2 + 14) and ghost["t"] == round(y2 + 14))
    check("幽灵宽度钳制（源元素 1264px 宽被压到 ~240px 内容宽 + 边框内边距）",
          240 <= ghost["w"] <= 260)
    check("拖拽中原元素半透明", page.evaluate(
        "document.querySelector('[data-page=\"1\"] .page-focus p').style.opacity"
    ) == "0.35")
    check("拖拽中手柄隐藏", page.evaluate(
        "document.getElementById('ve-drag-handle').style.display==='none'"
    ))

    page.mouse.up()
    page.wait_for_timeout(100)
    commit = last_msg(page, "ve:move:commit")
    check("松手发出 ve:move:commit（targetIndex=1：移到第二位）",
          commit is not None and commit["payload"]["targetIndex"] == 1)
    check("松手后元素透明度恢复", page.evaluate(
        "document.querySelector('[data-page=\"1\"] .page-focus p').style.opacity==='' || "
        "document.querySelector('[data-page=\"1\"] .page-focus p').style.opacity===''"
    ))
    check("松手后幽灵隐藏、手柄复显", page.evaluate(
        "document.getElementById('ve-drag-ghost').style.display==='none' && "
        "document.getElementById('ve-drag-handle').style.display==='block'"
    ))
    check("拖拽仅发补丁不动 DOM（由外部重放）", focus_texts(page, "1") == ["one", "two", "three"])

    apply(page, [{"kind": "move", "selector": '[data-page="1"] .page-focus p:nth-of-type(1)', "moveId": "oe-mv-5",
                  "targetIndex": 1}])
    check("提交的补丁重放后顺序生效", focus_texts(page, "1") == ["two", "one", "three"])
    page.close()

    b.close()

fails = [n for n, ok in results if not ok]
print("\n冒烟结论:", "FAIL — " + "; ".join(fails) if fails else f"PASS（{len(results)} 项）")
sys.exit(1 if fails else 0)
