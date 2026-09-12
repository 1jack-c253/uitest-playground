# -*- coding: utf-8 -*-
"""
决定性验证：移除 Playwright 默认的"禁用节流"参数，看后台标签页是否真的被节流。
对照上一次（未移除）的结果：采样间隔 246ms，visibilityState 从未变 hidden。
"""
import time
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


def run(label, **launch_kwargs):
    print("\n" + "=" * 72)
    print(f"【{label}】")
    print("=" * 72)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, **launch_kwargs)
        ctx = browser.new_context(viewport={"width": 1280, "height": 800})
        page = ctx.new_page()
        page.goto(f"{BASE}/progressbar", timeout=30000)
        page.evaluate(RECORDER)
        page.click("#startButton")
        page.wait_for_timeout(3000)

        other = ctx.new_page()
        other.goto(f"{BASE}/")
        other.bring_to_front()
        other.wait_for_timeout(10000)
        other.bring_to_front()
        page.bring_to_front()

        r = page.evaluate(
            """() => ({vis: window.__visLog, samples: window.__samples,
                       now: document.getElementById('progressBar').getAttribute('aria-valuenow')})"""
        )
        browser.close()

    vis = r["vis"]
    s = r["samples"]
    print(f"  visibilityState 变化：{vis if vis else '（从未变化，一直是 visible）'}")

    if len(s) >= 2:
        span = s[-1][0] - s[0][0]
        avg = span / len(s)
        print(f"  采样点 {len(s)} 个，跨度 {span}ms，平均间隔 {avg:.0f}ms（设定 250ms）")
        print(f"  间隔 > 1000ms 的采样点数量："
              f"{sum(1 for i in range(1, len(s)) if s[i][0]-s[i-1][0] > 1000)}")

    # 前台 vs 后台期间的进度增长
    fg = [x for x in s if x[0] <= 3000]
    bg = [x for x in s if 3000 < x[0] < 13000]
    if fg and len(fg) >= 2:
        print(f"  【前台 3 秒】进度 {fg[0][1]}% -> {fg[-1][1]}%  增长 {int(fg[-1][1])-int(fg[0][1])}")
    if bg and len(bg) >= 2:
        print(f"  【后台 10 秒】进度 {bg[0][1]}% -> {bg[-1][1]}%  增长 {int(bg[-1][1])-int(bg[0][1])}")
    print(f"  切回前台后 aria-valuenow = {r['now']}%")


run("对照组：Playwright 默认参数（节流被禁用）")
run("实验组：移除禁用节流的参数", ignore_default_args=STRIP)
