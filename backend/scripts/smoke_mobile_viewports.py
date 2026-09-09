"""移动端/平板视口实测：横向溢出 + 底部 Tab 栏 + 截图（供人工复核）"""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "http://localhost:3000"
TARGETS = ["/", "/login", "/register", "/html-workbench", "/materials", "/history", "/terms"]
OUT = Path(__file__).parent / "_mobile_shots"
OUT.mkdir(exist_ok=True)

fail = 0
with sync_playwright() as p:
    browser = p.chromium.launch()
    for w, h in [(375, 812), (768, 1024)]:
        ctx = browser.new_context(viewport={"width": w, "height": h}, device_scale_factor=2)
        page = ctx.new_page()
        for path in TARGETS:
            name = f"{w}_{path.strip('/').replace('/', '_') or 'home'}"
            try:
                page.goto(BASE + path, wait_until="load", timeout=30000)
                page.wait_for_timeout(1200)
                sw = page.evaluate("document.scrollingElement.scrollWidth")
                iw = page.evaluate("window.innerWidth")
                tab = page.evaluate("!!document.querySelector('.mobile-tabbar')")
                overflow = sw - iw
                status = "OK " if overflow <= 0 else "OVERFLOW"
                if overflow > 0:
                    fail += 1
                print(f"[{w}] {path:20s} {status} overflow={overflow}px tabbar={tab}")
                page.screenshot(path=str(OUT / f"{name}.png"))
            except Exception as e:
                fail += 1
                print(f"[{w}] {path:20s} ERROR {e}")
        ctx.close()
    browser.close()

print("FAILED" if fail else "ALL CLEAN")
sys.exit(1 if fail else 0)
