"""任务G4 代理级冒烟：浮动层（textbox/image/note）百分比坐标自由摆放

场景一：float 补丁物化到指定节（data-float 标记 / 百分比定位 / 节 position:relative / 幂等 / 清退）
场景二：拖拽落位（实时 px 钳制 + ve:float:commit 百分比回传 + 左缘 clamp=0）
场景三：点节内空白出「＋在此插入」菜单 → ve:float:create（textbox/note/image 三入口）
场景四：选中浮层出工具条（编辑/删除）→ ve:float:remove；双击行内编辑 → ve:float:content
场景五：与既有拖拽调序共存（拖浮层不发 move:commit；拖普通元素仍发 move:commit）
场景六：导出（浮层保留 data-float + % 定位；便签剔除；ve-ui 剥离）

前置：node --input-type=module -e "import('./src/components/v2editor/pickAgent.ts').then(m=>process.stdout.write(m.buildPickAgentScript('smoke-ch')))" 已生成 scripts/_agent_smoke.js
运行：PYTHONIOENCODING=utf-8 python scripts/smoke_v2_floats.py
"""

import sys
from pathlib import Path

sys.path.insert(0, ".")

from playwright.sync_api import sync_playwright

AGENT = Path("scripts/_agent_smoke.js").read_text(encoding="utf-8")

HTML = (
    "<html><head><style>section{display:block}</style></head><body>"
    '<main id="oe-content">'
    '<section class="oe-chapter" data-section="第一章">'
    '<section class="oe-section" data-sec="1" data-title="A" style="min-height:320px"><div class="page-focus"><p>one</p><p>two</p><p>three</p></div></section>'
    '<section class="oe-section" data-sec="2" data-title="B" style="min-height:320px"><div class="page-focus"><p>two-b</p></div></section>'
    '<section class="oe-section" data-sec="3" data-title="C" style="min-height:320px"><div class="page-focus"><p>three</p></div></section>'
    "</main>"
    '<script data-ve-agent="1">' + AGENT + "</script>"
    "</body></html>"
)


def float_html(fid, kind, left, top, width, content):
    return (
        f'<div data-float="1" data-oe-float="{fid}" data-float-kind="{kind}" '
        f'style="position:absolute;left:{left}%;top:{top}%;width:{width}%;z-index:30;'
        f'box-sizing:border-box;background:#fff;padding:10px">'
        f'<div class="ve-fl-text">{content}</div></div>'
    )


def float_patch(fid, kind, section, left, top, width, content):
    return {
        "kind": "float",
        "float": {"id": fid, "kind": kind, "section": section, "xPct": left, "yPct": top, "wPct": width, "content": content},
        "html": float_html(fid, kind, left, top, width, content),
    }


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


def msgs_of(page, mtype):
    return page.evaluate("t=>window.__msgs.filter(x=>x.type===t)", mtype)


def clear_msgs(page):
    page.evaluate("()=>{window.__msgs.length=0}")


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

    # ---- 场景一：float 补丁物化 / 幂等 / 清退 ----
    page = b.new_page()
    page.set_content(HTML, wait_until="load")
    fl1 = float_patch("oe-fl1", "textbox", 2, 20, 30, 32, "浮文本")
    fl2 = float_patch("oe-fl2", "note", 1, 5, 10, 22, "便签A")
    fl3 = float_patch("oe-fl3", "image", 2, 55, 15, 34, "")
    apply(page, [fl1, fl2, fl3])
    check("浮层落在指定节（节2 两个）", page.evaluate(
        "document.querySelectorAll('.oe-section[data-sec=\"2\"] > [data-oe-float]').length === 2"
        " && !!document.querySelector('.oe-section[data-sec=\"1\"] > [data-oe-float=\"oe-fl2\"]')"
        " && document.querySelectorAll('[data-oe-float]').length === 3"
    ))
    check("data-float 标记与百分比定位", page.evaluate(
        "() => { var f = document.querySelector('[data-oe-float=\"oe-fl1\"]');"
        "return f.getAttribute('data-float') === '1' && f.style.left === '20%' && f.style.top === '30%' && f.style.width === '32%'; }"
    ))
    check("所在节被置为定位上下文", page.evaluate(
        "getComputedStyle(document.querySelector('.oe-section[data-sec=\"2\"]')).position === 'relative'"
    ))
    apply(page, [fl1, fl2, fl3])
    check("重放幂等（不重复物化）", page.evaluate("document.querySelectorAll('[data-oe-float]').length === 3"))
    apply(page, [fl1, fl3])
    check("补丁清退后多余浮层移除", page.evaluate(
        "document.querySelectorAll('[data-oe-float]').length === 2 && !document.querySelector('[data-oe-float=\"oe-fl2\"]')"
    ))
    page.close()

    # ---- 场景二：拖拽落位 + clamp ----
    page = b.new_page()
    page.set_content(HTML, wait_until="load")
    collect_msgs(page)
    apply(page, [fl1])
    post(page, "ve:pick:set", {"enabled": True})

    box = page.locator('[data-oe-float="oe-fl1"]').bounding_box()
    sx, sy = page.evaluate(
        "() => { var r = document.querySelector('.oe-section[data-sec=\"2\"]').getBoundingClientRect();"
        "return [r.left, r.top]; }"
    )
    cx, cy = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
    page.mouse.move(cx, cy)
    page.mouse.down()
    page.mouse.move(sx - 60, sy + 40, steps=5)  # 拖出左缘
    page.wait_for_timeout(80)
    live = page.evaluate(
        "() => { var f = document.querySelector('[data-oe-float=\"oe-fl1\"]');"
        "return { l: parseFloat(f.style.left), t: parseFloat(f.style.top), op: f.style.opacity }; }"
    )
    check("拖拽中左缘钳制为 0px", live["l"] == 0)
    check("拖拽中半透明反馈", live["op"] == "0.6")
    page.mouse.up()
    page.wait_for_timeout(100)
    commits = msgs_of(page, "ve:float:commit")
    check("松手回传百分比坐标（xPct=0）", commits and commits[-1]["payload"]["xPct"] == 0)
    check("拖浮层不触发调序补丁", msgs_of(page, "ve:move:commit") == [])

    # 拖到节中部再落位
    page.mouse.move(15, 15)
    box = page.locator('[data-oe-float="oe-fl1"]').bounding_box()
    page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
    page.mouse.down()
    page.mouse.move(sx + 600, sy + 220, steps=5)
    page.mouse.up()
    page.wait_for_timeout(100)
    commits = msgs_of(page, "ve:float:commit")
    pct = commits[-1]["payload"] if commits else {}
    check("再次拖拽回传新坐标（xPct>0）", pct.get("xPct", -1) > 0 and 0 <= pct.get("yPct", -1) <= 100)
    updated = float_patch("oe-fl1", "textbox", 2, pct["xPct"], pct["yPct"], 32, "浮文本")
    apply(page, [updated])
    after = page.evaluate(
        "() => { var f = document.querySelector('[data-oe-float=\"oe-fl1\"]');"
        "var s = document.querySelector('.oe-section[data-sec=\"2\"]');"
        "return f.getBoundingClientRect().left - s.getBoundingClientRect().left; }"
    )
    check("按回传百分比重放位置一致", abs(after - pct["xPct"] / 100 * page.evaluate(
        "document.querySelector('.oe-section[data-sec=\"2\"]').clientWidth"
    )) < 2)
    page.close()

    # ---- 场景三：点空白出「＋在此插入」菜单 ----
    page = b.new_page()
    page.set_content(HTML, wait_until="load")
    collect_msgs(page)
    post(page, "ve:pick:set", {"enabled": True})
    sec2 = page.evaluate(
        "() => { var r = document.querySelector('.oe-section[data-sec=\"2\"]').getBoundingClientRect();"
        "return { x: r.left + r.width * 0.6, y: r.top + r.height * 0.85 }; }"
    )
    page.mouse.click(sec2["x"], sec2["y"])
    page.wait_for_timeout(100)
    check("点节内空白弹出插入菜单", page.evaluate(
        "() => { var m = document.getElementById('ve-float-menu');"
        "return !!m && m.style.display !== 'none' && m.textContent.indexOf('文本框') >= 0; }"
    ))
    page.evaluate("() => { [].forEach.call(document.getElementById('ve-float-menu').children, function(b){ if(b.textContent.indexOf('便签')>=0) b.click(); }); }")
    page.wait_for_timeout(100)
    creates = msgs_of(page, "ve:float:create")
    check("选便签发出创建意图（kind/section）", creates and creates[-1]["payload"]["kind"] == "note" and creates[-1]["payload"]["section"] == 2)
    check("创建坐标为点击点百分比（0-100）", 0 <= creates[-1]["payload"]["xPct"] <= 100 and 0 <= creates[-1]["payload"]["yPct"] <= 100)
    check("选择后菜单关闭", page.evaluate("!document.getElementById('ve-float-menu')"))
    page.close()

    # ---- 场景四：选中工具条 / 删除 / 行内编辑 ----
    page = b.new_page()
    page.set_content(HTML, wait_until="load")
    collect_msgs(page)
    apply(page, [fl1, float_patch("oe-fl2", "note", 2, 50, 50, 22, "便签内容")])
    post(page, "ve:pick:set", {"enabled": True})

    note = page.locator('[data-oe-float="oe-fl2"]')
    note.click()
    page.wait_for_timeout(100)
    picked = msgs_of(page, "ve:pick")
    check("点击浮层选中并出工具条", bool(picked) and page.evaluate("!!document.getElementById('ve-float-bar')"))
    page.evaluate("() => { [].forEach.call(document.getElementById('ve-float-bar').children, function(b){ if(b.textContent.indexOf('删除')>=0) b.click(); }); }")
    page.wait_for_timeout(100)
    removes = msgs_of(page, "ve:float:remove")
    check("工具条删除发出移除意图", bool(removes) and removes[-1]["payload"]["id"] == "oe-fl2")

    txt = page.locator('[data-oe-float="oe-fl1"] .ve-fl-text')
    txt.dblclick()
    page.wait_for_timeout(80)
    page.keyboard.type("改写后的内容")
    page.keyboard.press("Enter")
    page.wait_for_timeout(100)
    contents = msgs_of(page, "ve:float:content")
    check("双击行内编辑提交浮层内容", contents and contents[-1]["payload"]["id"] == "oe-fl1" and contents[-1]["payload"]["text"].find("改写后的内容") >= 0)
    page.close()

    # ---- 场景五：与既有拖拽调序共存 ----
    page = b.new_page()
    page.set_content(HTML, wait_until="load")
    collect_msgs(page)
    move_p2 = {"kind": "move", "selector": '[data-sec="1"] .page-focus p:nth-of-type(1)', "moveId": "oe-mv-2", "targetIndex": 2}
    apply(page, [fl1, move_p2])
    post(page, "ve:pick:set", {"enabled": True})
    check("move 补丁与 float 补丁同场生效", page.evaluate(
        "!!document.querySelector('[data-oe-float=\"oe-fl1\"]') && document.querySelectorAll('[data-sec=\"1\"] .page-focus p').length === 3"
    ))
    first_p = page.locator('[data-sec="1"] .page-focus p').first
    first_p.click()
    page.wait_for_timeout(100)
    h = page.locator("#ve-drag-handle")
    hr = h.bounding_box()
    page.mouse.move(hr["x"] + 6, hr["y"] + 6)
    page.mouse.down()
    page.mouse.move(hr["x"] + 36, hr["y"] + 60, steps=5)
    page.mouse.up()
    page.wait_for_timeout(100)
    check("普通元素经手柄拖拽仍走调序补丁", msgs_of(page, "ve:move:commit") != [])
    page.close()

    # ---- 场景六：导出 ----
    page = b.new_page()
    page.set_content(HTML, wait_until="load")
    apply(page, [fl1, float_patch("oe-fl2", "note", 3, 10, 10, 22, "私密便签"), fl3])
    post(page, "ve:pick:set", {"enabled": True})
    page.wait_for_timeout(100)
    exported = export_html(page)
    check("导出保留浮层与百分比定位", 'data-float="1"' in exported and 'left:20%;top:30%;width:32%' in exported)
    check("导出剔除便签（默认不导出）", "私密便签" not in exported and 'data-float-kind="note"' not in exported)
    check("导出剥离编辑 UI", "ve-float-menu" not in exported and "ve-float-bar" not in exported and "ve-float-cursor" not in exported)
    check("导出保留节定位上下文", 'style="min-height:320px; position: relative;"' in exported or "position: relative" in exported)

    # 重开语义：导出剥离了 agent 脚本与便签，新页面重注入 agent 后同批补丁重放不重复。
    # 必须换新页面：同页 set_content 走 document.write 复用 window，旧 agent 闭包与其
    # 300ms MutationObserver 重放定时器存活，会在新文档里重放含便签的旧补丁清单（拟真度缺陷，非产品 bug）
    reopened = exported.replace("</body>", '<script data-ve-agent="1">' + AGENT + "</script></body>")
    page.close()
    page = b.new_page()
    page.set_content(reopened, wait_until="load")
    page.wait_for_timeout(100)
    apply(page, [fl1, fl3])
    check("重开重放幂等（无重复浮层）", page.evaluate("document.querySelectorAll('[data-oe-float]').length === 2"))
    page.close()

    b.close()

fails = [n for n, ok in results if not ok]
print("\n冒烟结论:", "FAIL — " + "; ".join(fails) if fails else f"PASS（{len(results)} 项）")
sys.exit(1 if fails else 0)
