# -*- coding: utf-8 -*-
"""
把靶场各页面的 JavaScript 扒出来，直接看它的实现逻辑。
这比任何猜测都可靠 —— 延迟到底是不是随机的、文案会不会变，
答案就写在源码里。
"""
from playwright.sync_api import sync_playwright

BASE = "http://uitestingplayground.com"
PAGES = [
    ("AJAX Data", "/ajax"),
    ("Client Side Delay", "/clientdelay"),
    ("Click", "/click"),
    ("Text Input", "/textinput"),
    ("Progress Bar", "/progressbar"),
    ("Dynamic ID", "/dynamicid"),
]

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    for label, path in PAGES:
        page.goto(BASE + path, timeout=30000)
        page.wait_for_timeout(500)

        print("\n" + "#" * 74)
        print(f"# {label}   {BASE + path}")
        print("#" * 74)

        # 外部脚本地址
        scripts = page.evaluate(
            "() => Array.from(document.scripts).map(s => s.src || '(inline)')"
        )
        print(f"  脚本列表: {scripts}")

        # 抓取每个外部脚本内容里与逻辑相关的片段
        for src in scripts:
            if src == "(inline)":
                continue
            body = page.evaluate(
                """async (u) => {
                    try {
                        const r = await fetch(u);
                        return await r.text();
                    } catch (e) { return 'FETCH_FAILED: ' + e; }
                }""",
                src,
            )
            name = src.rsplit("/", 1)[-1]
            print(f"\n  ------ {name} ------")
            # 只打印含关键字的行，避免刷屏
            keys = ["ajax", "delay", "timeout", "setTimeout", "Random", "random",
                    "progress", "click", "change", "input", "visibility", "id",
                    "button", "Appear", "Loaded", "Data"]
            lines = body.splitlines()
            for i, line in enumerate(lines):
                low = line.lower()
                if any(k.lower() in low for k in keys) and len(line.strip()) > 3:
                    print(f"    {i+1:>4}| {line.strip()[:150]}")

        # 内联脚本
        inline = page.evaluate(
            """() => Array.from(document.scripts)
                    .filter(s => !s.src)
                    .map(s => s.textContent.trim())
                    .filter(t => t.length > 0)"""
        )
        if inline:
            print(f"\n  ------ 内联脚本（{len(inline)} 段）------")
            for seg in inline:
                for line in seg.splitlines():
                    if len(line.strip()) > 3:
                        print(f"    {line.strip()[:150]}")

    browser.close()
