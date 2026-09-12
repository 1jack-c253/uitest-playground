# -*- coding: utf-8 -*-
"""
终极验证：用独立的浏览器窗口遮挡进度条窗口。
（Playwright 切标签页不会让页面 hidden，但独立 context 会开新窗口，
  窗口被遮挡 + 移除 --disable-backgrounding-occluded-windows 即可触发节流）
"""
from playwright.sync_api import sync_playwright

BASE = "http://uitestingplayground.com"
STRIP = [
    "--disable-background-timer-throttling",
    "--disable-backgrounding-occluded-windows",
    "--disable-renderer-backgrounding",
]

RECORDER = """
() => {
    window.__visLog = [];
    window.__samples = [];
    const t0 = Date.now();
    document.addEventListener('visibilitychange', () => {
        window.__visLog.push([Date.now() - t0, document.visibilityState]);
    });
    const bar = document.getElementById('progressBar');
    window.__tick = setInterval(() => {
        window.__samples.push([Date.now() - t0, bar.getAttribute('aria-valuenow')]);
    }, 250);
    return true;
}
"""

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False, ignore_default_args=STRIP)

    # 窗口 A：进度条
    ctxA = browser.new_context(viewport={"width": 900, "height": 600})
    pageA = ctxA.new_page()
    pageA.goto(f"{BASE}/progressbar", timeout=30000)
    pageA.evaluate(RECORDER)
    pageA.click("#startButton")
    pageA.wait_for_timeout(3000)

    # 窗口 B：独立 context = 独立窗口，置顶遮挡 A
    ctxB = browser.new_context(viewport={"width": 1400, "height": 900})
    pageB = ctxB.new_page()
    pageB.goto(f"{BASE}/", timeout=30000)
    pageB.bring_to_front()
    pageB.wait_for_timeout(12000)

    r = pageA.evaluate(
        """() => ({vis: window.__visLog, samples: window.__samples,
                   now: document.getElementById('progressBar').getAttribute('aria-valuenow')})"""
    )

    print("=" * 72)
    print("窗口遮挡实验（已移除禁用节流的 3 个参数）")
    print("=" * 72)
    print(f"  visibilityState 变化：{r['vis'] if r['vis'] else '（未变化）'}")

    s = r["samples"]
    if len(s) >= 2:
        span = s[-1][0] - s[0][0]
        print(f"  采样点 {len(s)} 个，跨度 {span}ms，平均间隔 {span/len(s):.0f}ms")
        gaps = [s[i][0] - s[i-1][0] for i in range(1, len(s))]
        big = [g for g in gaps if g > 1000]
        print(f"  间隔 >1000ms 的次数：{len(big)}   最大间隔：{max(gaps) if gaps else 0}ms")

    fg = [x for x in s if x[0] <= 3000]
    bg = [x for x in s if x[0] > 3000]
    if fg and len(fg) >= 2:
        print(f"  【遮挡前 3 秒】进度 {fg[0][1]}% -> {fg[-1][1]}%  增长 {int(fg[-1][1])-int(fg[0][1])}")
    if bg and len(bg) >= 2:
        print(f"  【遮挡中 12 秒】进度 {bg[0][1]}% -> {bg[-1][1]}%  增长 {int(bg[-1][1])-int(bg[0][1])}")
    print(f"  结束时 aria-valuenow = {r['now']}%")

    browser.close()
