# -*- coding: utf-8 -*-
"""
缺陷 D1 的严格重测。
上一次的错误：wait_for_selector(".bg-success") 在第二次点击后会立即返回
（第一次的结果还在页面上），导致只等了 2 秒就误判"spinner 未复位"。
这次改成等结果条数真正增加。
"""
from playwright.sync_api import sync_playwright

BASE = "http://uitestingplayground.com"

SPINNER = """() => {
    const s = document.querySelector('.spinner-border, .fa-spinner, .spinner, #spinner');
    if (!s) return 'no-element';
    return getComputedStyle(s).display;
}"""

COUNT = "() => document.querySelectorAll('.bg-success').length"
# wait_for_function 用的是表达式，不是函数定义
COUNT_EXPR = "document.querySelectorAll('.bg-success').length"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    page.goto(f"{BASE}/ajax", timeout=30000)

    print("=" * 72)
    print("缺陷 D1 严格重测")
    print("=" * 72)
    print(f"  初始：结果条数={page.evaluate(COUNT)}  spinner.display={page.evaluate(SPINNER)}")

    # 第一次
    page.click("#ajaxButton")
    page.wait_for_timeout(800)
    print(f"  首次点击后 0.8s：条数={page.evaluate(COUNT)}  spinner={page.evaluate(SPINNER)}")
    page.wait_for_function(f"{COUNT_EXPR} === 1", timeout=120000)
    page.wait_for_timeout(1000)
    print(f"  ✅ 首次完成（条数=1）：spinner = {page.evaluate(SPINNER)}")

    # 第二次 —— 等条数真正变成 2
    page.click("#ajaxButton")
    page.wait_for_timeout(800)
    print(f"  二次点击后 0.8s：条数={page.evaluate(COUNT)}  spinner={page.evaluate(SPINNER)}")
    page.wait_for_function(f"{COUNT_EXPR} === 2", timeout=120000)
    page.wait_for_timeout(1000)
    print(f"  ✅ 二次完成（条数=2）：spinner = {page.evaluate(SPINNER)}   <-- 关键看这里")

    # 第三次，确认累积行为
    page.click("#ajaxButton")
    page.wait_for_function(f"{COUNT_EXPR} === 3", timeout=120000)
    page.wait_for_timeout(800)
    n = page.evaluate(COUNT)
    print(f"  三次完成：条数={n}（累积不清理，源码里是 appendChild）")
    print(f"  spinner = {page.evaluate(SPINNER)}")

    print()
    print("  页面上三条结果的内容：")
    for i, t in enumerate(page.locator(".bg-success").all_inner_texts()):
        print(f"    [{i+1}] {t!r}")

    browser.close()
