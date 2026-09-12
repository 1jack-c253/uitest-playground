# -*- coding: utf-8 -*-
"""
侦察脚本：一次性摸清 UI Test Automation Playground 6 个场景的真实 DOM 结构。
不跑长延迟，只做结构扫描，目的是拿到准确的选择器。
"""
from playwright.sync_api import sync_playwright

BASE = "http://uitestingplayground.com"

PAGES = [
    ("主页", "/"),
    ("Dynamic ID", "/dynamicid"),
    ("AJAX Data", "/ajax"),
    ("Client Side Delay", "/clientdelay"),
    ("Click", "/click"),
    ("Text Input", "/textinput"),
    ("Progress Bar", "/progressbar"),
]


def dump(page, label):
    print("=" * 70)
    print(f"【{label}】 {page.url}")
    print(f"  title = {page.title()!r}")

    # 页面上的说明文字（scenario 描述）
    try:
        h3 = page.locator("h3")
        if h3.count():
            print(f"  说明: {h3.first.inner_text()[:160]!r}")
    except Exception:
        pass

    # 扫描所有可交互控件
    for el in page.locator("button, input, a.btn, #progressBar, [role=progressbar]").all():
        try:
            info = el.evaluate(
                """e => ({
                    tag: e.tagName,
                    id: e.id || '',
                    cls: (typeof e.className === 'string' ? e.className : ''),
                    name: e.name || '',
                    type: e.type || '',
                    text: (e.innerText || e.value || '').slice(0, 45),
                    visible: !!(e.offsetWidth || e.offsetHeight)
                })"""
            )
            print(f"    -> {info}")
        except Exception as ex:
            print(f"    -> [读取失败] {ex}")


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # 环境信息
        page.goto(BASE)
        dpr = page.evaluate("window.devicePixelRatio")
        ua = page.evaluate("navigator.userAgent")
        print("#" * 70)
        print(f"环境：devicePixelRatio = {dpr}")
        print(f"环境：viewport = {page.viewport_size}")
        print(f"环境：UA = {ua[:90]}")
        print("#" * 70)

        for label, path in PAGES:
            try:
                page.goto(BASE + path, timeout=30000)
                page.wait_for_timeout(800)
                dump(page, label)
            except Exception as ex:
                print("=" * 70)
                print(f"【{label}】打开失败：{ex}")

        browser.close()
        print("\n侦察完成。")


if __name__ == "__main__":
    main()
