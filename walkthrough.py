# -*- coding: utf-8 -*-
"""
带你看一遍 —— 交互式走查脚本

用法（在 Git Bash 里）：
    PY="/c/Users/Administrator/AppData/Local/Programs/Python/Python313/python.exe"
    PYTHONUTF8=1 "$PY" walkthrough.py

每到一个现场脚本会停下来，等你看清楚浏览器窗口，再按回车继续。
浏览器窗口会一直开着，你随时可以自己动手点两下。
"""
import os
import sys
import time
from playwright.sync_api import sync_playwright

BASE = "http://uitestingplayground.com"

# 加 --auto 参数（或设环境变量 AUTO=1）就自动推进，不等回车
AUTO_MODE = ("--auto" in sys.argv) or (os.environ.get("AUTO") == "1")

# 自动模式下，每个停点给你留多少秒看浏览器
AUTO_PAUSE_SECONDS = int(os.environ.get("PAUSE_SECONDS", "15"))


def pause(msg):
    print()
    print("  " + "-" * 66)
    print(f"  👀 {msg}")
    print("  " + "-" * 66)
    if not AUTO_MODE:
        # 真实终端 —— 等你按回车
        input("  >>> 看清楚了就按回车继续...")
    else:
        # 自动模式 —— 倒计时继续
        print(f"  >>> 你有 {AUTO_PAUSE_SECONDS} 秒看浏览器，然后自动继续")
        for i in range(AUTO_PAUSE_SECONDS, 0, -1):
            print(f"      ⏳ {i:>2} 秒...")
            time.sleep(1)
        print("      ▶  继续！")
    print()


def goto(page, path, tries=4):
    """带重试的跳转 —— 练习站点偶尔会限流或抽风，不能一次失败就挂掉。"""
    url = path if path.startswith("http") else BASE + path
    last = None
    for i in range(tries):
        try:
            page.goto(url, timeout=45000)
            return
        except Exception as e:
            last = e
            wait = 3 * (i + 1)
            print(f"  ⚠️  打开 {url} 失败（第 {i+1} 次），{wait} 秒后重试...")
            time.sleep(wait)
    raise last


def wait_enter(prompt, auto_seconds=3):
    """真终端里等回车；自动模式等几秒。"""
    if not AUTO_MODE:
        input(prompt)
    else:
        print(f"{prompt}（自动模式，{auto_seconds} 秒后继续）")
        time.sleep(auto_seconds)


def head(n, title):
    print("\n\n" + "█" * 70)
    print(f"█  第 {n} 站：{title}")
    print("█" * 70)


with sync_playwright() as p:
    browser = p.chromium.launch(headless=False, slow_mo=120)
    ctx = browser.new_context(viewport={"width": 1100, "height": 800})
    page = ctx.new_page()

    # ==================================================================
    head(1, "动态 ID —— 按钮的身份证每次都换")
    goto(page, "/dynamicid")
    page.wait_for_timeout(800)

    btn = page.locator("button.btn-primary").first
    id_before = btn.get_attribute("id")
    print(f"""
  页面上那个蓝色按钮，它的 id 是：

      {id_before}

  现在请你【自己按 F5 刷新这个浏览器窗口】，或者看脚本帮你刷。
""")
    wait_enter("  >>> 按回车，脚本帮你刷新页面...", auto_seconds=4)

    page.reload()
    page.wait_for_timeout(800)
    id_after = page.locator("button.btn-primary").first.get_attribute("id")
    print(f"""
  刷新之后的 id 是：

      {id_after}

  👉 对比一下上面那个 —— {'不一样！每次刷新都换。' if id_before != id_after else '居然一样？'}

  所以如果你代码里写死「找 id = {id_before[:20]}... 的按钮」，
  第二次跑就找不到它了。

  但注意看：按钮上的字一直没变，class 也一直没变 ——
  这就是为什么"改用文本 / class 定位"能解决问题。
""")
    pause("看看浏览器里那个按钮，它还在那儿，只是身份证换了")

    # ==================================================================
    head(2, "Click —— 程序点的它不认，只有真鼠标才行")
    goto(page, "/click")
    page.wait_for_timeout(800)

    PROBE = """() => {
        window.__ev = [];
        document.body.addEventListener('click', (e) => {
            window.__ev.push({screenX: e.screenX, isTrusted: e.isTrusted});
        }, true);
    }"""
    page.evaluate(PROBE)

    def show(label):
        r = page.evaluate("""() => ({
            cls: document.getElementById('badButton').className,
            ev: window.__ev.slice(-1)[0] || null
        })""")
        color = "🟢 变绿了" if "success" in r["cls"] else "🔵 没变"
        e = r["ev"]
        extra = (f"｜处理器收到的 screenX = {e['screenX']}，isTrusted = {e['isTrusted']}"
                 if e else "｜（处理器没收到事件）")
        print(f"     {label}：{color} {extra}")

    print("""
  这个按钮的说明是「Button That Ignores DOM Click Event」。

  站点源码里它的判断条件是这两行：

      if (event.target.id == 'badButton')
          if (event.screenX > 0)                              ← 关键在这
              event.target.className = 'btn btn-success';     // 变绿

  我已经装了一个【事件探针】，能看见处理器实际收到的事件参数。
""")
    pause("确认按钮现在是蓝色的")

    print("\n  ① 派发一个「合成」click 事件（程序造出来的）...")
    page.locator("#badButton").dispatch_event("click")
    page.wait_for_timeout(600)
    show("结果")

    print("\n  ② 用 JS 直接调 element.click()...")
    page.evaluate("() => document.getElementById('badButton').click()")
    page.wait_for_timeout(600)
    show("结果")

    pause("看到按钮还是蓝色的吧？两次程序点击都没用")

    print("\n  ③ 换真实鼠标：把鼠标真的移过去、按下、抬起...\n")
    box = page.locator("#badButton").bounding_box()
    cx, cy = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
    print(f"     元素中心 CSS 坐标：({cx:.0f}, {cy:.0f})")
    print(f"     系统缩放 125% → 物理坐标约 ({cx * 1.25:.0f}, {cy * 1.25:.0f})")
    page.mouse.move(cx, cy)
    page.mouse.down()
    page.mouse.up()
    page.wait_for_timeout(600)
    show("结果")

    pause("看浏览器 —— 按钮现在应该是绿色的")

    print("""
  🔬 最后做一次「铁证实验」：造一个合成事件，但手动把 screenX 填成大于 0。
     如果按钮变绿 —— 就证明判据是 screenX，不是 isTrusted。
""")
    goto(page, "/click")
    page.wait_for_timeout(700)
    page.evaluate(PROBE)
    page.evaluate("""() => {
        const b = document.getElementById('badButton');
        const r = b.getBoundingClientRect();
        b.dispatchEvent(new MouseEvent('click', {
            bubbles: true, cancelable: true,
            screenX: r.left + 10, screenY: r.top + 10
        }));
    }""")
    page.wait_for_timeout(600)
    show("④ 合成事件 + 手动填 screenX")

    print("""
  👉 注意看上面那个 isTrusted —— 它还是 False（说明不是真人点的），
     但因为 screenX 大于 0，按钮照样变绿。

     ⭐ 结论：判据是 screenX，不是 isTrusted。
""")
    pause("看浏览器 —— 按钮应该是绿色的")

    # ==================================================================
    head(3, "长延迟 —— 点一下要等十几秒")
    goto(page, "/ajax")
    page.wait_for_timeout(500)
    print("""
  现在点这个按钮，它会去跟服务器要数据。

  ⚠️ 注意看：点完之后会出现一个转圈，而且【要转十几秒】才出结果。

  这就是为什么"固定超时"会出问题：
    - 你设等 10 秒  → 页面还没好 → 报错（假失败，其实程序没毛病）
    - 你设等 60 秒  → 每次都白等十几秒，30 条用例跑下来几十分钟

  正确做法：显式轮询等待 —— 不停问"好了没"，一好就往下走。
""")
    pause("准备好了就按回车，我们点它")
    page.click("#ajaxButton")
    t0 = time.time()
    print(f"  已点击，开始计时... 现在是 {time.strftime('%H:%M:%S')}")
    page.wait_for_selector(".bg-success", timeout=120000)
    dt = time.time() - t0
    print(f"  ✅ 结果出来了，实测用了 {dt:.1f} 秒")
    print(f"     返回内容：{page.locator('.bg-success').first.inner_text()!r}")

    pause("看浏览器里的结果条")

    # ==================================================================
    head(4, "结果累积 —— 点 3 次，堆 3 条")
    print("""
  现在连点这个按钮 —— 看它会【追加】结果，而不是【覆盖】。

  源码里是这么写的：
      document.getElementById("content").appendChild(label);

  「appendChild」= 往后面追加一条，从来不清空之前的。
""")
    for i in range(3):
        page.click("#ajaxButton")
        print(f"  第 {i+2} 次点击...")
        page.wait_for_function(
            f"document.querySelectorAll('.bg-success').length === {i+2}",
            timeout=120000,
        )
    page.wait_for_timeout(500)
    n = page.locator(".bg-success").count()
    print(f"\n  👉 现在页面上有 {n} 条结果了，一模一样的内容堆在一起。")
    print("     这就是「多次触发结果累积无清理机制」—— 真实缺陷，源码+实测双确认。")

    pause("看看浏览器里堆了几条结果")

    # ==================================================================
    head(5, "Text Input —— 少触发一个事件就白填")
    goto(page, "/textinput")
    page.wait_for_timeout(500)
    inp = page.locator("#newButtonName")
    upd = page.locator("#updatingButton")

    print(f"""
  这个输入框要求：input 和 change 【两个事件的值一致】才会更新按钮文案。

  当前按钮文案：{upd.inner_text()!r}
""")
    pause("记住现在按钮上的字")

    print("  ① 正常输入（fill 会同时触发 input 和 change）...")
    inp.fill("MyButton")
    upd.click()
    page.wait_for_timeout(500)
    print(f"     按钮变成了：{upd.inner_text()!r}   ✅ 正常")

    print("\n  ② 只触发 input，不触发 change（模拟自动化框架的坑）...")
    page.evaluate("""() => {
        const el = document.getElementById('newButtonName');
        el.value = 'OnlyInput';
        el.dispatchEvent(new Event('input', {bubbles: true}));
    }""")
    upd.click()
    page.wait_for_timeout(500)
    print(f"     按钮变成了：{upd.inner_text()!r}   ❌ 没更新！")
    print("     👉 输入框里明明写着 OnlyInput，按钮上的字却没变")

    pause("★ 最关键的一眼 —— 输入框里是 OnlyInput，按钮上却还是 MyButton")

    print("\n  ③ 现在把输入框清空，再点一次...")
    inp.fill("")
    upd.click()
    page.wait_for_timeout(500)
    print(f"     按钮变成了：{upd.inner_text()!r}   ❌ 还是没更新")

    pause("再看一眼：输入框已经空了，按钮上还是旧的 MyButton")

    # ==================================================================
    head(6, "进度条 + 系统缩放")
    goto(page, "/progressbar")
    page.wait_for_timeout(500)
    bar = page.locator("#progressBar")
    print(f"""
  进度条当前：aria-valuenow = {bar.get_attribute('aria-valuenow')}，文字 = {bar.inner_text()!r}

  ⚠️ 注意：要读进度，应该读 aria-valuenow 这个属性，而不是 innerHTML 文本。
     （文本是给人看的，aria 属性是给机器读的，更稳定）
""")
    pause("确认进度条停在 25%")

    page.click("#startButton")
    print("  已点击 Start，你看进度条在跑...")
    page.wait_for_timeout(4000)
    print(f"  4 秒后：aria-valuenow = {bar.get_attribute('aria-valuenow')}")
    page.click("#stopButton")
    page.wait_for_timeout(500)
    res = page.locator("#result")
    if res.count():
        print(f"  Stop 后 Result = {res.inner_text()!r}")

    print(f"""
  关于「后台标签页定时器节流」：

  Chromium 在页面不可见时会故意放慢页面里的定时器来省电。
  但你用 Playwright 跑的时候【看不到这个现象】，因为 Playwright
  启动浏览器时默认带了这些参数：

      --disable-background-timer-throttling
      --disable-backgrounding-occluded-windows
      --disable-renderer-backgrounding

  也就是说：这个坑真实存在，只是自动化框架帮你绕过去了。
""")

    print("\n" + "█" * 70)
    print("█  走查完成 —— 6 个现场你都亲眼看过了")
    print("█" * 70)
    wait_enter("\n  >>> 按回车关闭浏览器...", auto_seconds=6)
    browser.close()
