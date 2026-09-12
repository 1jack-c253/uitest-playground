# -*- coding: utf-8 -*-
"""
专项：验证 Chromium 后台标签页定时器节流。
关键点：不能用 page.evaluate 去查状态——它会把页面重新激活，
        改成让页面自己记录 visibilitychange 和进度采样。
"""
import time
from playwright.sync_api import sync_playwright

BASE = "http://uitestingplayground.com"

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


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        ctx = browser.new_context(viewport={"width": 1280, "height": 800})
        page = ctx.new_page()

        # 先埋点，再开始
        page.goto(f"{BASE}/progressbar", timeout=30000)
        page.evaluate(RECORDER)
        page.click("#startButton")
        page.wait_for_timeout(3000)

        fg_start = page.evaluate("() => window.__samples.slice(-1)[0][1]")

        # 打开第二个标签并切过去，让进度条页进入后台
        other = ctx.new_page()
        other.goto(f"{BASE}/")
        other.bring_to_front()
        # 关键：这段时间只用 other 等待，绝不碰 page
        t0 = time.time()
        other.wait_for_timeout(10000)
        elapsed = time.time() - t0

        # 切回来之前先把后台期间的数据捞出来
        other.bring_to_front()
        page.bring_to_front()
        result = page.evaluate(
            """() => ({
                vis: window.__visLog,
                samples: window.__samples,
                now: document.getElementById('progressBar').getAttribute('aria-valuenow')
            })"""
        )

        print("=" * 72)
        print("后台标签页定时器节流 —— 验证结果")
        print("=" * 72)
        print(f"\nvisibilityState 变化记录（时间ms, 状态）：")
        for t, v in result["vis"]:
            print(f"    t={t:>7}ms  -> {v}")

        print(f"\n进度采样（时间ms, aria-valuenow）：")
        samples = result["samples"]
        for t, v in samples:
            print(f"    t={t:>7}ms  -> {v}%")

        if samples:
            print(f"\n采样点总数 = {len(samples)}")
            if len(samples) >= 2:
                span = samples[-1][0] - samples[0][0]
                print(f"采样跨度为 {span}ms，平均每 {span/len(samples):.0f}ms 一个点"
                      f"（前台时应约 250ms 一个点）")

            # 找出后台期间（t 落在切换后）的进度增长
            bg = [s for s in samples if s[0] > 3000 and s[0] < 13000]
            if bg:
                print(f"\n后台期间（约 t=3000~13000ms）进度：{bg[0][1]}% -> {bg[-1][1]}%"
                      f"  增长 {int(bg[-1][1]) - int(bg[0][1])}")
            fg = [s for s in samples if s[0] <= 3000]
            if fg and len(fg) >= 2:
                print(f"前台期间（t<=3000ms）进度：{fg[0][1]}% -> {fg[-1][1]}%"
                      f"  增长 {int(fg[-1][1]) - int(fg[0][1])}")

        print(f"\n当前（已切回前台）aria-valuenow = {result['now']}%")
        browser.close()


if __name__ == "__main__":
    main()
