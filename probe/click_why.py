# -*- coding: utf-8 -*-
"""
排查：为什么 walkthrough.py 里合成点击会生效，而独立测试里不生效？
唯一可疑的差异：walkthrough 用了 slow_mo=120 + new_context(viewport=...)
逐个变量做对照。
"""
from playwright.sync_api import sync_playwright

URL = "http://uitestingplayground.com/click"

PROBE = """
() => {
    window.__events = [];
    document.body.addEventListener('click', (e) => {
        window.__events.push({screenX: e.screenX, isTrusted: e.isTrusted});
    }, true);
    return true;
}
"""


def trial(label, use_slow_mo, use_context):
    with sync_playwright() as p:
        kw = {"headless": False}
        if use_slow_mo:
            kw["slow_mo"] = 120
        browser = p.chromium.launch(**kw)
        if use_context:
            page = browser.new_context(viewport={"width": 1100, "height": 800}).new_page()
        else:
            page = browser.new_page()

        page.goto(URL, timeout=45000)
        page.wait_for_timeout(800)
        page.evaluate(PROBE)

        b = page.locator("#badButton")
        before = b.get_attribute("class")
        b.dispatch_event("click")
        page.wait_for_timeout(800)
        after = b.get_attribute("class")
        ev = page.evaluate("() => window.__events")

        print(f"  {label:<46} 点击前={before.split()[-1]:<12} "
              f"点击后={after.split()[-1]:<12} "
              f"探针={[(e['screenX'], e['isTrusted']) for e in ev]}")
        browser.close()


print("=" * 110)
print("对照实验：dispatch_event('click') 在不同启动配置下的效果")
print("=" * 110)
trial("① 默认（无 slow_mo，browser.new_page）", False, False)
trial("② slow_mo=120，browser.new_page", True, False)
trial("③ 无 slow_mo，new_context(viewport=1100x800)", False, True)
trial("④ slow_mo=120 + new_context(viewport=1100x800)  ← walkthrough 的配置", True, True)
print("=" * 110)
