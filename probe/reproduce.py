# -*- coding: utf-8 -*-
"""
问题复现脚本：把简历里声称的每一个技术难题，在真实浏览器里复现一次。
用有头模式（headed），因为部分现象在 headless 下不会出现。
"""
import time
from playwright.sync_api import sync_playwright

BASE = "http://uitestingplayground.com"


def section(n, title):
    print("\n" + "=" * 72)
    print(f"[{n}] {title}")
    print("=" * 72)


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=0)
        ctx = browser.new_context(viewport={"width": 1280, "height": 800})
        page = ctx.new_page()

        # ---------------------------------------------------------------
        section(1, "环境：屏幕缩放 / devicePixelRatio")
        page.goto(BASE, timeout=30000)
        env = page.evaluate(
            """() => ({
                dpr: window.devicePixelRatio,
                screenW: screen.width, screenH: screen.height,
                outerW: window.outerWidth, outerH: window.outerHeight,
                innerW: window.innerWidth, innerH: window.innerHeight,
                availW: screen.availWidth, availH: screen.availHeight
            })"""
        )
        print(f"  devicePixelRatio = {env['dpr']}   <-- 1.25 就说明系统缩放是 125%")
        print(f"  screen  = {env['screenW']} x {env['screenH']}")
        print(f"  avail   = {env['availW']} x {env['availH']}")
        print(f"  window  = outer {env['outerW']}x{env['outerH']} / inner {env['innerW']}x{env['innerH']}")

        # ---------------------------------------------------------------
        section(2, "动态 ID：刷新后 id 变化，旧 id 失效")
        page.goto(f"{BASE}/dynamicid", timeout=30000)
        btn = page.locator("button.btn-primary").first
        id1 = btn.get_attribute("id")
        cls = btn.get_attribute("class")
        txt = btn.inner_text()
        page.reload()
        id2 = page.locator("button.btn-primary").first.get_attribute("id")
        print(f"  刷新前 id = {id1}")
        print(f"  刷新后 id = {id2}")
        print(f"  id 是否变化 = {id1 != id2}")
        print(f"  稳定不变的 class = {cls!r}")
        print(f"  稳定不变的文本   = {txt!r}")

        # 用旧 id 去定位，验证会失败
        page.evaluate(
            "(oldId) => { window.__oldStillResolves = !!document.getElementById(oldId); }", id1
        )
        still = page.evaluate("() => window.__oldStillResolves")
        print(f"  用刷新前的旧 id 在当前页面查找 = {still}  (false 表示定位失效)")

        # ---------------------------------------------------------------
        section(3, "Click：合成 click 无效，真实鼠标点击才生效")
        page.goto(f"{BASE}/click", timeout=30000)
        bad = page.locator("#badButton")
        print(f"  初始 class = {bad.get_attribute('class')!r}")

        # 3a. 用 JS 派发合成 click
        bad.dispatch_event("click")
        page.wait_for_timeout(600)
        after_synth = bad.get_attribute("class")
        print(f"  ① 派发合成 click 之后  class = {after_synth!r}")

        # 3b. 用 JS 直接调 element.click()
        page.evaluate("() => document.getElementById('badButton').click()")
        page.wait_for_timeout(600)
        after_js = bad.get_attribute("class")
        print(f"  ② 执行 JS element.click() 之后 class = {after_js!r}")

        # 3c. 真实的鼠标坐标点击（move -> down -> up）
        box = bad.bounding_box()
        print(f"  bounding_box = {box}")
        cx, cy = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
        print(f"  计算出的元素中心 CSS 坐标 = ({cx:.1f}, {cy:.1f})")
        page.mouse.move(cx, cy)
        page.mouse.down()
        page.mouse.up()
        page.wait_for_timeout(600)
        after_real = bad.get_attribute("class")
        print(f"  ③ 真实坐标鼠标 down/up 之后 class = {after_real!r}  <-- 变绿才算成功")
        print(f"  按钮文案 = {bad.inner_text()!r}")

        # ---------------------------------------------------------------
        section(4, "AJAX Data：实测延迟时长 + 等待策略")
        page.goto(f"{BASE}/ajax", timeout=30000)
        page.click("#ajaxButton")
        t0 = time.time()
        spin = page.locator(".spinner-border, .fa-spinner").first
        print(f"  点击后 spinner 可见 = {spin.is_visible()}")
        page.wait_for_selector(".bg-success", timeout=90000)
        dt = time.time() - t0
        print(f"  >>> 实测 AJAX 延迟 = {dt:.1f} 秒")
        print(f"  返回文本 = {page.locator('.bg-success').inner_text()!r}")

        # 二次触发，观察缺陷
        page.click("#ajaxButton")
        page.wait_for_timeout(1200)
        spin2 = page.locator(".spinner-border, .fa-spinner").first
        print(f"  二次点击后：spinner 可见 = {spin2.is_visible()}；"
              f"结果文案 = {page.locator('.bg-success').inner_text()!r}")

        # ---------------------------------------------------------------
        section(5, "Client Side Delay：实测延迟时长")
        page.goto(f"{BASE}/clientdelay", timeout=30000)
        page.click("#ajaxButton")
        t0 = time.time()
        page.wait_for_selector(".bg-success", timeout=90000)
        dt = time.time() - t0
        print(f"  >>> 实测客户端延迟 = {dt:.1f} 秒")
        print(f"  返回文本 = {page.locator('.bg-success').inner_text()!r}")

        # ---------------------------------------------------------------
        section(6, "Text Input：input/change 双事件")
        page.goto(f"{BASE}/textinput", timeout=30000)
        inp = page.locator("#newButtonName")
        upd = page.locator("#updatingButton")
        print(f"  初始按钮文案 = {upd.inner_text()!r}")

        # 标准 fill（会同时触发 input 和 change）
        inp.fill("MyButton")
        upd.click()
        print(f"  fill('MyButton') 后点击 -> 按钮 = {upd.inner_text()!r}")

        # 只触发 input 不触发 change
        page.evaluate(
            """() => {
                const el = document.getElementById('newButtonName');
                el.value = 'OnlyInput';
                el.dispatchEvent(new Event('input', {bubbles: true}));
            }"""
        )
        upd.click()
        print(f"  只触发 input 不触发 change 后点击 -> 按钮 = {upd.inner_text()!r}")

        # 清空后点击
        inp.fill("")
        upd.click()
        print(f"  清空输入后点击 -> 按钮 = {upd.inner_text()!r}")

        # ---------------------------------------------------------------
        section(7, "Progress Bar：aria-valuenow + 后台标签页定时器节流")
        page.goto(f"{BASE}/progressbar", timeout=30000)
        bar = page.locator("#progressBar")
        print(f"  初始 aria-valuenow = {bar.get_attribute('aria-valuenow')}")
        print(f"  初始文本 = {bar.inner_text()!r}")

        # 7a. 前台跑 6 秒
        page.click("#startButton")
        print(f"  点击 Start 后 visibilityState = {page.evaluate('() => document.visibilityState')}")
        t0 = time.time()
        page.wait_for_timeout(6000)
        fg = int(bar.get_attribute("aria-valuenow"))
        print(f"  【前台】运行 {time.time()-t0:.1f} 秒 -> aria-valuenow = {fg}")

        # 7b. 开新标签页，让原页面进入后台，再跑 6 秒
        page.click("#stopButton")
        page.click("#startButton")
        before_bg = int(bar.get_attribute("aria-valuenow"))
        other = ctx.new_page()
        other.goto("about:blank")
        other.bring_to_front()
        page.wait_for_timeout(300)
        vis = page.evaluate("() => document.visibilityState")
        t0 = time.time()
        page.wait_for_timeout(6000)
        after_bg = int(bar.get_attribute("aria-valuenow"))
        print(f"  【后台】visibilityState = {vis}")
        print(f"  【后台】运行 {time.time()-t0:.1f} 秒 -> aria-valuenow 从 {before_bg} 变成 {after_bg}"
              f"  (增长 {after_bg - before_bg})")
        print(f"  >>> 前台 6 秒增长 {fg - 25}，后台 6 秒增长 {after_bg - before_bg}")

        other.close()
        page.bring_to_front()
        page.click("#stopButton")
        print(f"  Stop 后 Result = {page.locator('#result').inner_text()!r}"
              if page.locator("#result").count() else "")

        browser.close()
        print("\n问题复现完成。")


if __name__ == "__main__":
    main()
