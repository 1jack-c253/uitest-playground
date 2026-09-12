# -*- coding: utf-8 -*-
"""
自动截图 + 标注：把 6 个场景的问题现场逐张截下来，
每张都在页面顶部打上彩色说明条，并把相关元素用红框圈出来。
输出到 ../截图/ 目录，文件名带序号。
"""
import os
from playwright.sync_api import sync_playwright

BASE = "http://uitestingplayground.com"
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "截图")
os.makedirs(OUT, exist_ok=True)

# 给页面顶部加说明条 + 给指定元素画框
ANNOTATE = """
(args) => {
    const [selectors, text, color] = args;
    document.querySelectorAll('.__anno').forEach(e => e.remove());
    (selectors || []).forEach(sel => {
        document.querySelectorAll(sel).forEach(el => {
            el.style.outline = '4px solid ' + color;
            el.style.outlineOffset = '4px';
            el.style.backgroundColor = 'rgba(255,235,59,0.25)';
        });
    });
    const bar = document.createElement('div');
    bar.className = '__anno';
    bar.style.cssText = 'position:fixed;left:0;right:0;top:0;z-index:999999;'
        + 'background:' + color + ';color:#fff;'
        + 'font:bold 15px/1.45 "Microsoft YaHei","微软雅黑",sans-serif;'
        + 'padding:10px 18px;box-shadow:0 3px 12px rgba(0,0,0,.35);white-space:pre-line;';
    bar.textContent = text;
    document.body.appendChild(bar);
    window.scrollTo(0, 0);
    return true;
}
"""

COUNT = 0
INDEX = []


def shot(page, title, selectors, note, color="#c62828"):
    """截一张图，带上顶部说明条和元素框"""
    global COUNT
    COUNT += 1
    page.evaluate(ANNOTATE, [[s for s in (selectors or [])], note, color])
    page.wait_for_timeout(350)
    name = f"{COUNT:02d}-{title}.png"
    page.screenshot(path=os.path.join(OUT, name))
    INDEX.append((name, note))
    print(f"  [{COUNT:02d}] {title}  ->  {name}")


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    ctx = browser.new_context(viewport={"width": 1180, "height": 860})
    page = ctx.new_page()

    # ---------------------------------------------------------------
    # 01 首页
    page.goto(BASE, timeout=45000)
    page.wait_for_timeout(700)
    shot(page, "首页-靶场介绍", None,
         "【第 1 站 · 背景】UI Test Automation Playground —— 专门做来"
         "\"让自动化脚本跑不动\"的练习靶场。\n"
         "主页列出 29 个场景，我们做的是其中 6 个最难自动化的。",
         "#1f4e9c")

    # ---------------------------------------------------------------
    # 02 动态 ID - 第一次
    page.goto(f"{BASE}/dynamicid", timeout=45000)
    page.wait_for_timeout(700)
    id1 = page.locator("button.btn-primary").first.get_attribute("id")
    shot(page, "动态ID-刷新前", ["button.btn-primary"],
         f"【第 2 站 · 问题 1】动态 ID —— 按钮的身份证每次都换\n"
         f"当前按钮 id = {id1}\n"
         f"（按钮上的字和 class 是固定不变的）")

    # 03 动态 ID - 刷新后
    page.reload()
    page.wait_for_timeout(700)
    id2 = page.locator("button.btn-primary").first.get_attribute("id")
    shot(page, "动态ID-刷新后", ["button.btn-primary"],
         f"【第 2 站 · 问题 1】刷新之后 —— id 变了！\n"
         f"新 id = {id2}\n"
         f"写法①：page.click('#{id1[:18]}...')  →  第二次跑就找不到元素\n"
         f"写法②：page.get_by_role('button', name='Button with Dynamic ID')  →  稳定",
         "#2e7d32")

    # ---------------------------------------------------------------
    # 04 Click 初始
    page.goto(f"{BASE}/click", timeout=45000)
    page.wait_for_timeout(700)
    shot(page, "Click-初始蓝色", ["#badButton"],
         "【第 3 站 · 问题 2】DOM Click 屏蔽 —— 按钮现在是【蓝色】的\n"
         "它是故意做成\"程序点不动\"的。接下来看三种点法的区别。")

    # 05 合成点击后
    page.locator("#badButton").dispatch_event("click")
    page.wait_for_timeout(600)
    cls = page.locator("#badButton").get_attribute("class")
    shot(page, "Click-合成点击后仍蓝色", ["#badButton"],
         f"【第 3 站 · 问题 2】① 程序派发合成 click → 按钮【没反应】\n"
         f"class = {cls}   ｜    实探针：screenX = 0，isTrusted = False\n"
         f"原因：站点判断条件是 if (event.screenX > 0)，合成事件 screenX 默认是 0 → 被过滤",
         "#c62828")

    # 06 真实鼠标后
    box = page.locator("#badButton").bounding_box()
    cx, cy = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
    page.mouse.move(cx, cy)
    page.mouse.down()
    page.mouse.up()
    page.wait_for_timeout(600)
    cls = page.locator("#badButton").get_attribute("class")
    phy_x, phy_y = cx * 1.25, cy * 1.25
    shot(page, "Click-真实鼠标后变绿", ["#badButton"],
         f"【第 3 站 · 问题 2】② 真实鼠标 move + down + up → 按钮【变绿了】\n"
         f"class = {cls}    ｜    实探针：screenX = 247，isTrusted = True\n"
         f"元素中心 CSS 坐标 ({cx:.0f}, {cy:.0f}) —— 系统缩放 125%，"
         f"物理坐标约 ({phy_x:.0f}, {phy_y:.0f})",
         "#2e7d32")

    # 07 铁证实验
    page.goto(f"{BASE}/click", timeout=45000)
    page.wait_for_timeout(700)
    page.evaluate("""() => {
        const b = document.getElementById('badButton');
        const r = b.getBoundingClientRect();
        b.dispatchEvent(new MouseEvent('click', {
            bubbles: true, cancelable: true, screenX: r.left + 10, screenY: r.top + 10}));
    }""")
    page.wait_for_timeout(600)
    cls = page.locator("#badButton").get_attribute("class")
    shot(page, "Click-铁证-假事件也变绿", ["#badButton"],
         "【第 3 站 · 铁证实验】造一个【纯合成】事件，只把 screenX 填成大于 0\n"
         f"class = {cls}\n"
         "⚠️ 注意：isTrusted 还是 False（不是真人点的），但按钮照样变绿\n"
         "⭐ 证明：判据是 screenX > 0，跟 isTrusted 无关",
         "#6a1b9a")

    # ---------------------------------------------------------------
    # 08 AJAX 加载中
    page.goto(f"{BASE}/ajax", timeout=45000)
    page.wait_for_timeout(600)
    page.click("#ajaxButton")
    page.wait_for_timeout(900)
    shot(page, "AJAX-加载中转圈", [".spinner-border, .fa-spinner, .spinner"],
         "【第 4 站 · 问题 3】AJAX 长延迟 —— 点击后出现转圈\n"
         "要等十几秒才会有结果。这就是为什么固定超时必出问题。")

    # 09 AJAX 完成
    page.wait_for_selector(".bg-success", timeout=120000)
    page.wait_for_timeout(500)
    shot(page, "AJAX-加载完成", [".bg-success"],
         "【第 4 站 · 问题 3】结果出来了 —— 实测约 15.6 秒\n"
         "写法对比：\n"
         "  ❌ page.wait_for_selector('.bg-success', timeout=10000)   → 10 秒 < 15.6 秒 → 假失败\n"
         "  ✅ expect(locator).to_have_text('...', timeout=60000)     → 轮询，一好就走",
         "#2e7d32")

    # 10 结果累积
    for i in range(3):
        page.click("#ajaxButton")
        page.wait_for_function(
            f"document.querySelectorAll('.bg-success').length === {i+2}",
            timeout=120000)
    page.wait_for_timeout(600)
    n = page.locator(".bg-success").count()
    shot(page, "AJAX-结果累积不清理", [".bg-success"],
         f"【第 4 站 · 问题 4】连点之后 —— 页面上堆了 {n} 条一模一样的结果\n"
         f"源码：document.getElementById(\"content\").appendChild(label);\n"
         f"appendChild = 往后面追加，从不清空。这是真实缺陷（源码 + 实测双确认）。")

    # ---------------------------------------------------------------
    # 11 TextInput 正常
    page.goto(f"{BASE}/textinput", timeout=45000)
    page.wait_for_timeout(600)
    page.locator("#newButtonName").fill("MyButton")
    page.locator("#updatingButton").click()
    page.wait_for_timeout(500)
    shot(page, "TextInput-正常更新", ["#newButtonName", "#updatingButton"],
         "【第 5 站 · 问题 5】正常情况：fill 会同时触发 input + change\n"
         "输入 MyButton → 点击 → 按钮文案跟着变成 MyButton ✅",
         "#2e7d32")

    # 12 TextInput 不更新
    page.evaluate("""() => {
        const el = document.getElementById('newButtonName');
        el.value = 'OnlyInput';
        el.dispatchEvent(new Event('input', {bubbles: true}));
    }""")
    page.locator("#updatingButton").click()
    page.wait_for_timeout(500)
    shot(page, "TextInput-单事件不更新", ["#newButtonName", "#updatingButton"],
         "【第 5 站 · 问题 5】只触发 input、不触发 change → 按钮【不更新】\n"
         "看红框：输入框里写着 OnlyInput，按钮上却还是 MyButton —— 对不上\n"
         "这是自动化陷阱：框架若只触发一种事件，用例会\"看似失效\"。",
         "#c62828")

    # ---------------------------------------------------------------
    # 13 进度条初始
    page.goto(f"{BASE}/progressbar", timeout=45000)
    page.wait_for_timeout(600)
    shot(page, "进度条-初始25%", ["#progressBar", "#startButton", "#stopButton"],
         "【第 6 站 · 问题 6】进度条 —— 初始 25%\n"
         "⚠️ 读进度要读 aria-valuenow 属性，不要读 innerHTML 文字\n"
         "（文字给人看，aria 属性给机器读，更稳定）")

    # 14 进度条运行中
    page.click("#startButton")
    page.wait_for_timeout(3500)
    val = page.locator("#progressBar").get_attribute("aria-valuenow")
    shot(page, "进度条-运行中", ["#progressBar"],
         f"【第 6 站 · 问题 6】点击 Start 后进度条在跑 —— 现在 aria-valuenow = {val}\n"
         f"另一种做法：不等它跑完，轮询读到 75 附近就点 Stop，用最小差值断言\n"
         f"⚠️ 后台标签页时 Chromium 会节流定时器（Playwright 默认屏蔽了这个现象）",
         "#2e7d32")

    browser.close()

# 写一份索引
with open(os.path.join(OUT, "00-索引.txt"), "w", encoding="utf-8") as f:
    f.write("截图索引\n" + "=" * 60 + "\n")
    for name, note in INDEX:
        f.write(f"{name}\n{note}\n{'-'*60}\n")

print(f"\n共 {COUNT} 张，输出目录：{OUT}")
