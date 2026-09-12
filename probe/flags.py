# -*- coding: utf-8 -*-
"""
查看 Playwright 启动 Chromium 时到底带了哪些命令行参数，
重点找 background / throttling / renderer 相关的 flag。
"""
from playwright.sync_api import sync_playwright

KEYWORDS = ["background", "throttl", "renderer", "occlud", "timer", "visible"]


def cmdline_of(browser):
    page = browser.new_page()
    page.goto("chrome://version/", timeout=30000)
    txt = page.locator("#command_line").inner_text()
    page.close()
    return txt


def show(title, cmdline):
    print("=" * 72)
    print(title)
    print("=" * 72)
    hits = []
    for token in cmdline.split():
        low = token.lower()
        if any(k in low for k in KEYWORDS):
            hits.append(token)
    if hits:
        for h in hits:
            print(f"    {h}")
    else:
        print("    （没有匹配的 flag）")
    return hits


with sync_playwright() as p:
    # ① 默认启动
    b1 = p.chromium.launch(headless=False)
    line1 = cmdline_of(b1)
    hits1 = show("① Playwright 默认启动参数中的节流相关 flag", line1)
    b1.close()

    # ② 主动移除这几个 flag
    ignore = [h for h in hits1]
    print()
    b2 = p.chromium.launch(headless=False, ignore_default_args=ignore)
    line2 = cmdline_of(b2)
    hits2 = show("② 移除这些 flag 之后再启动", line2)
    b2.close()

    print()
    print("=" * 72)
    print(f"结论：默认带了 {len(hits1)} 个节流相关 flag；移除后剩 {len(hits2)} 个")
    print("=" * 72)
