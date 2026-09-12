# -*- coding: utf-8 -*-
"""
决定性测试：Click 场景到底认哪种点击方式？

装一个事件探针，把 site 的处理器【实际收到的】事件参数打出来
（screenX / screenY / isTrusted / type），
而不是只看按钮最后变没变绿 —— 因为变绿可能被别的方式带偏。
"""
from playwright.sync_api import sync_playwright

BASE = "http://uitestingplayground.com"
URL = f"{BASE}/click"

PROBE = """
() => {
    window.__events = [];
    document.body.addEventListener('click', (e) => {
        window.__events.push({
            target: e.target.id || e.target.tagName,
            type: e.type,
            screenX: e.screenX,
            screenY: e.screenY,
            clientX: e.clientX,
            clientY: e.clientY,
            isTrusted: e.isTrusted
        });
    }, true);
    return true;
}
"""

READ = """() => ({
    cls: document.getElementById('badButton').className,
    events: window.__events
})"""


def report(label, r):
    print(f"\n  【{label}】")
    print(f"     按钮 class = {r['cls']!r}"
          f"   {'🟢 变绿' if 'success' in r['cls'] else '🔵 没变'}")
    for e in r["events"]:
        print(f"     探针收到: type={e['type']} target={e['target']!r} "
              f"screenX={e['screenX']} screenY={e['screenY']} "
              f"clientX={e['clientX']} isTrusted={e['isTrusted']}")


with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()

    def fresh():
        page.goto(URL, timeout=45000)
        page.wait_for_timeout(700)
        page.evaluate(PROBE)

    print("=" * 74)
    print("Click 场景 —— 四种点击方式对照（每次都是全新加载的页面）")
    print("=" * 74)
    print("\n  站点逻辑：  if (event.target.id == 'badButton') { if (event.screenX > 0) 变绿 }")

    # A. Playwright 的 dispatch_event
    fresh()
    page.locator("#badButton").dispatch_event("click")
    page.wait_for_timeout(500)
    report("A. locator.dispatch_event('click')", page.evaluate(READ))

    # B. 纯 JS element.click()
    fresh()
    page.evaluate("() => document.getElementById('badButton').click()")
    page.wait_for_timeout(500)
    report("B. JS 原生 element.click()", page.evaluate(READ))

    # C. Playwright 的 locator.click()（走真实输入通道）
    fresh()
    page.locator("#badButton").click()
    page.wait_for_timeout(500)
    report("C. Playwright locator.click()", page.evaluate(READ))

    # D. 手动真实鼠标 move/down/up
    fresh()
    box = page.locator("#badButton").bounding_box()
    cx, cy = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
    page.mouse.move(cx, cy)
    page.mouse.down()
    page.mouse.up()
    page.wait_for_timeout(500)
    report("D. page.mouse move + down + up", page.evaluate(READ))

    # E. 手工构造带 screenX 的合成事件（验证 screenX 就是判据）
    fresh()
    page.evaluate("""() => {
        const b = document.getElementById('badButton');
        const r = b.getBoundingClientRect();
        b.dispatchEvent(new MouseEvent('click', {
            bubbles: true, cancelable: true,
            screenX: r.left + 10, screenY: r.top + 10
        }));
    }""")
    page.wait_for_timeout(500)
    report("E. 合成事件但手动填 screenX>0", page.evaluate(READ))

    browser.close()
