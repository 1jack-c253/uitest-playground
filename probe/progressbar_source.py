# -*- coding: utf-8 -*-
"""
进度条页面：读源码 + 实测 Result 的含义。
页面 Scenario 说："停在 75% 附近，差值越小成绩越好" —— 验证 Result 到底是不是"停止值 - 75"。
"""
from playwright.sync_api import sync_playwright

URL = "http://uitestingplayground.com/progressbar"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()

    # ---------- 1. 读源码 ----------
    page.goto(URL, timeout=45000)
    page.wait_for_timeout(600)
    print("=" * 74)
    print("Progress Bar 页面 —— 完整内联脚本")
    print("=" * 74)
    segs = page.evaluate(
        """() => Array.from(document.scripts).filter(s => !s.src)
                .map(s => s.textContent).filter(t => t.trim().length > 0)"""
    )
    for i, seg in enumerate(segs, 1):
        if "progress" in seg.lower() or "Start" in seg or "Stop" in seg or "Result" in seg:
            print(f"\n----- 第 {i} 段 -----")
            print(seg.strip()[:3000])

    # ---------- 2. 实测 Result ----------
    print("\n" + "=" * 74)
    print("实测：在不同进度值停，看 Result 是多少")
    print("=" * 74)
    print(f"{'停下来的值':>12} | {'Result 显示':>28} | 差值(值-75)")
    print("-" * 74)

    for target in (40, 60, 90):
        page.goto(URL, timeout=45000)
        page.wait_for_timeout(500)
        page.click("#startButton")

        # 在浏览器内轮询，到目标值立刻停
        page.wait_for_function(
            f"parseInt(document.querySelector('#progressBar').getAttribute('aria-valuenow')) >= {target}",
            polling=5,
        )
        page.click("#stopButton")
        page.wait_for_timeout(400)

        stopped = page.locator("#progressBar").get_attribute("aria-valuenow")
        result = page.locator("#result").inner_text()
        print(f"{stopped:>12} | {result:>28} | {int(stopped) - 75}")

    browser.close()
