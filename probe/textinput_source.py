# -*- coding: utf-8 -*-
"""把 Text Input 页面的完整内联脚本原样打出来，看它到底什么逻辑。"""
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto("http://uitestingplayground.com/textinput", timeout=45000)
    page.wait_for_timeout(600)

    print("=" * 74)
    print("Text Input 页面 —— 完整内联脚本")
    print("=" * 74)
    segs = page.evaluate(
        """() => Array.from(document.scripts)
                .filter(s => !s.src)
                .map(s => s.textContent)
                .filter(t => t.trim().length > 0)"""
    )
    for i, seg in enumerate(segs, 1):
        print(f"\n----- 第 {i} 段 -----")
        print(seg.strip())

    print("\n" + "=" * 74)
    print("页面上的输入框和按钮的初始 HTML")
    print("=" * 74)
    print(page.evaluate(
        """() => document.querySelector('#newButtonName').outerHTML
              + '\\n' + document.querySelector('#updatingButton').outerHTML"""
    ))
    browser.close()
