# -*- coding: utf-8 -*-
"""
验证：Playwright 的 page.mouse.move() 会不会移动【操作系统的真实鼠标指针】？

方法：用 Windows API 直接读系统光标坐标，在 Playwright 移动鼠标前后各读一次。
"""
import ctypes
import time
from playwright.sync_api import sync_playwright


class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


def cursor_pos():
    pt = POINT()
    ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
    return pt.x, pt.y


with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    page.goto("http://uitestingplayground.com/click", timeout=45000)
    page.wait_for_timeout(1200)

    print("=" * 74)
    print("Playwright 的 mouse.move 会不会移动操作系统的真实光标？")
    print("=" * 74)

    x0, y0 = cursor_pos()
    print(f"\n  开浏览器后，系统光标位置 = ({x0}, {y0})")

    box = page.locator("#badButton").bounding_box()
    cx, cy = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
    print(f"\n  现在让 Playwright 把\"鼠标\"移到按钮中心 —— CSS 坐标 ({cx:.0f}, {cy:.0f})")
    page.mouse.move(cx, cy)
    page.wait_for_timeout(500)

    x1, y1 = cursor_pos()
    print(f"  移动之后，系统光标位置 = ({x1}, {y1})")
    print(f"  系统光标有没有动？ {'动了' if (x0, y0) != (x1, y1) else '★ 没动 —— 完全没变'}")

    print(f"\n  再来一次，这次移到屏幕最角落 (1500, 900)")
    page.mouse.move(1500, 900)
    page.wait_for_timeout(500)
    x2, y2 = cursor_pos()
    print(f"  移动之后，系统光标位置 = ({x2}, {y2})")
    print(f"  系统光标有没有动？ {'动了' if (x1, y1) != (x2, y2) else '★ 没动 —— 完全没变'}")

    # 真实点击按钮，看按钮反应 + 系统光标
    print(f"\n  ---- 现在用 page.mouse.down()/up() 真的点一下按钮 ----")
    x3, y3 = cursor_pos()
    page.mouse.move(cx, cy)
    page.mouse.down()
    page.mouse.up()
    page.wait_for_timeout(600)
    x4, y4 = cursor_pos()
    cls = page.locator("#badButton").get_attribute("class")
    print(f"  按钮 class = {cls}   {'🟢 变绿（点击生效）' if 'success' in cls else '🔵 没变'}")
    print(f"  系统光标：({x3}, {y3}) → ({x4}, {y4})   "
          f"{'动了' if (x3, y3) != (x4, y4) else '★ 还是没动'}")

    print("""
  ────────────────────────────────────────────────────────────────
  结论：Playwright 的 mouse API 【不会移动操作系统的真实鼠标指针】。
        它是通过 CDP（Chrome 调试协议）把输入事件直接注入浏览器的
        输入管线，跳过了操作系统这一层。
  ────────────────────────────────────────────────────────────────
""")
    input("  按回车关闭浏览器...")
    browser.close()
