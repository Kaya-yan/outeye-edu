"""登录态移动端/平板视口实测：API 打桩进入受保护页面，测溢出 + 底部 Tab + V2 编辑器布局"""
import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "http://localhost:3000"
OUT = Path(__file__).parent / "_mobile_shots"
OUT.mkdir(exist_ok=True)

STUB_HTML = (
    "<!DOCTYPE html><html><head><style>body{margin:0;font-family:sans-serif;padding:24px}"
    "h1{font-size:28px}p{font-size:16px;line-height:1.6}</style></head><body>"
    "<h1>The Jeaning of America</h1><p>Smoke stub page for layout test.</p></body></html>"
)
PROJECT = {
    "id": "proj-smoke",
    "title": "The Jeaning of America",
    "mode": "slides",
    "source_type": "from_plan",
    "status": "in_editing",
    "current_version_id": "v1",
    "source_meta": {},
    "versions": [
        {
            "id": "v1",
            "version_number": 1,
            "save_type": "auto",
            "editor_schema_json": None,
            "rendered_html": STUB_HTML,
            "change_summary": None,
            "created_at": "2026-09-09T00:00:00Z",
        }
    ],
}
USER = {"id": "u1", "email": "t@example.com", "full_name": "测试教师"}

TARGETS = ["/", "/materials", "/history", "/profile", "/courseware/proj-smoke/edit-v2"]

fail = 0
with sync_playwright() as p:
    browser = p.chromium.launch()
    for w, h in [(375, 812), (768, 1024)]:
        ctx = browser.new_context(viewport={"width": w, "height": h}, device_scale_factor=2)
        ctx.add_cookies([{"name": "auth_token", "value": "stub-token", "url": BASE}])

        def stub(route):
            url = route.request.url
            if "/users/me" in url:
                body = USER
            elif "/courseware/proj-smoke" in url and "edit" not in url:
                body = PROJECT
            elif "/projects" in url or "/components" in url or "/knowledge" in url:
                body = []
            else:
                body = {}
            route.fulfill(status=200, content_type="application/json", body=json.dumps(body))

        ctx.route("**/api/v1/**", stub)
        page = ctx.new_page()
        # 播种 localStorage 登录态（AuthProvider 挂载时读取）
        page.goto(BASE + "/login", wait_until="load")
        page.evaluate(
            "([t, u]) => { localStorage.setItem('token', t); localStorage.setItem('user', u); }",
            ["stub-token", json.dumps(USER, ensure_ascii=False)],
        )

        for path in TARGETS:
            name = f"{w}_{path.strip('/').replace('/', '_')}"
            try:
                page.goto(BASE + path, wait_until="load", timeout=30000)
                page.wait_for_timeout(1500)
                sw = page.evaluate("document.scrollingElement.scrollWidth")
                iw = page.evaluate("window.innerWidth")
                tab = page.evaluate("!!document.querySelector('.mobile-tabbar')")
                overflow = sw - iw
                status = "OK " if overflow <= 0 else "OVERFLOW"
                if overflow > 0:
                    fail += 1
                print(f"[{w}] {path:40s} {status} overflow={overflow}px tabbar={tab}")
                page.screenshot(path=str(OUT / f"{name}.png"))
            except Exception as e:
                fail += 1
                print(f"[{w}] {path:40s} ERROR {e}")
        ctx.close()
    browser.close()

print("FAILED" if fail else "ALL CLEAN")
sys.exit(1 if fail else 0)
