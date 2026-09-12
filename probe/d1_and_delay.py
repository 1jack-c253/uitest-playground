# -*- coding: utf-8 -*-
"""
专项 1：验证 AJAX 延迟是否是随机的（跑 3 次取时长）
专项 2：验证缺陷 D1 —— 加载完成后再点一次，spinner 是否未复位、文案是否变化
"""
import time
from playwright.sync_api import sync_playwright

BASE = "http://uitestingplayground.com"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()

    print("=" * 72)
    print("专项 1：AJAX 延迟是否随机（连续 3 次）")
    print("=" * 72)
    delays = []
    for i in range(3):
        page.goto(f"{BASE}/ajax", timeout=30000)
        page.click("#ajaxButton")
        t0 = time.time()
        page.wait_for_selector(".bg-success", timeout=120000)
        dt = time.time() - t0
        delays.append(dt)
        print(f"  第 {i+1} 次：{dt:.1f} 秒")
    print(f"  => 延迟范围 {min(delays):.1f}s ~ {max(delays):.1f}s，"
          f"是否随机 = {max(delays) - min(delays) > 3}")

    print()
    print("=" * 72)
    print("专项 2：缺陷 D1 —— 二次触发后的 spinner 与文案状态")
    print("=" * 72)
    page.goto(f"{BASE}/ajax", timeout=30000)

    def spinner_state():
        return page.evaluate(
            """() => {
                const s = document.querySelector('.spinner-border, .fa-spinner, .spinner');
                if (!s) return 'no-spinner-element';
                const cs = getComputedStyle(s);
                return cs.display + '/' + cs.visibility;
            }"""
        )

    def result_text():
        el = page.locator(".bg-success")
        return el.inner_text() if el.count() else "(无结果)"

    print(f"  ① 初始：spinner = {spinner_state()}；结果 = {result_text()!r}")

    page.click("#ajaxButton")
    print(f"  ② 首次点击后 1s：spinner = {spinner_state()}；结果 = {result_text()!r}")
    page.wait_for_selector(".bg-success", timeout=120000)
    t_first = page.locator(".bg-success").inner_text()
    print(f"  ③ 首次加载完成：spinner = {spinner_state()}；结果 = {t_first!r}")

    page.wait_for_timeout(1500)
    print(f"  ④ 等待 1.5s 后：spinner = {spinner_state()}；结果 = {result_text()!r}")

    # 二次触发
    page.click("#ajaxButton")
    page.wait_for_timeout(1500)
    print(f"  ⑤ 二次点击后 1.5s：spinner = {spinner_state()}；结果 = {result_text()!r}")

    page.wait_for_selector(".bg-success", timeout=120000)
    page.wait_for_timeout(2000)   # 等稳定
    t_second = page.locator(".bg-success").inner_text()
    print(f"  ⑥ 二次加载完成后：spinner = {spinner_state()}；结果 = {t_second!r}")
    print(f"     结果数量 = {page.locator('.bg-success').count()}")
    print(f"     文案是否变化 = {t_first != t_second}")
    print(f"     spinner 是否仍显示 = {spinner_state()}")

    # 页面 HTML 语言
    print(f"  页面 lang 属性 = {page.evaluate('() => document.documentElement.lang')!r}")
    print(f"  navigator.language = {page.evaluate('() => navigator.language')!r}")

    browser.close()
