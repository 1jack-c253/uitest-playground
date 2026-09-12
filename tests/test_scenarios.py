# -*- coding: utf-8 -*-
"""
UI Test Automation Playground —— 6 个抗自动化场景的 pytest 测试套件。

设计原则：
  · 断言基于页面真实机制（读源码确认），而非表面现象
  · 长延迟场景使用显式轮询等待，不使用固定 sleep
  · 判定性优先：断言「确定的机制」而不是「不确定的耗时」
"""
import re

import pytest
from playwright.sync_api import sync_playwright, expect

BASE = "http://uitestingplayground.com"


# ----------------------------------------------------------------------
# fixtures
# ----------------------------------------------------------------------

@pytest.fixture(scope="session")
def browser():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        yield browser
        browser.close()


@pytest.fixture
def page(browser):
    ctx = browser.new_context()
    pg = ctx.new_page()
    pg.set_default_timeout(60_000)
    yield pg
    ctx.close()


# ----------------------------------------------------------------------
# 场景 1：Dynamic ID
# ----------------------------------------------------------------------

def test_dynamic_id_changes_on_reload(page):
    """按钮 id 为随机 UUID，每次刷新都变；class 与文本恒定不变。"""
    page.goto(f"{BASE}/dynamicid")
    btn = page.locator("button.btn-primary").first

    id_first = btn.get_attribute("id")
    assert re.fullmatch(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
                        id_first), f"id 应为 UUID 格式，实际 {id_first!r}"

    page.reload()
    id_second = page.locator("button.btn-primary").first.get_attribute("id")

    assert id_first != id_second, "刷新后 id 应发生变化"
    # 正因为 id 不可靠，才需要改用这几个稳定特征定位
    assert page.locator("button.btn-primary").first.get_attribute("class") == "btn btn-primary"
    assert page.get_by_role("button", name="Button with Dynamic ID").count() == 1


# ----------------------------------------------------------------------
# 场景 2：Click —— 合成点击被过滤
# ----------------------------------------------------------------------

def test_click_synthetic_event_is_ignored(page):
    """JS 合成 click 事件 screenX 恒为 0，被页面过滤。"""
    page.goto(f"{BASE}/click")
    bad = page.locator("#badButton")
    assert "btn-primary" in bad.get_attribute("class")

    bad.dispatch_event("click")
    page.wait_for_timeout(500)

    assert "btn-success" not in bad.get_attribute("class"), \
        "合成事件不应让按钮变绿"


def test_click_real_mouse_event_works(page):
    """带真实屏幕坐标的鼠标事件才生效。"""
    page.goto(f"{BASE}/click")
    bad = page.locator("#badButton")

    bad.click()  # Playwright 走真实输入通道

    expect(bad).to_have_class(re.compile("btn-success"))


def test_click_judgement_is_screenx_not_istrusted(page):
    """
    铁证：构造一个纯合成事件（isTrusted 必为 False），
    仅将 screenX 填为大于 0 —— 按钮依然变绿。

    证明页面的判据是 `event.screenX > 0`，与 isTrusted 无关。
    """
    page.goto(f"{BASE}/click")

    page.evaluate(
        """() => {
            const b = document.getElementById('badButton');
            const r = b.getBoundingClientRect();
            b.dispatchEvent(new MouseEvent('click', {
                bubbles: true, cancelable: true,
                screenX: r.left + 10, screenY: r.top + 10
            }));
        }"""
    )

    expect(page.locator("#badButton")).to_have_class(re.compile("btn-success"))


# ----------------------------------------------------------------------
# 场景 3：Text Input —— input / change 双事件
# ----------------------------------------------------------------------

def test_text_input_requires_both_events(page):
    """只触发 input 不触发 change，按钮不更新。"""
    page.goto(f"{BASE}/textinput")
    upd = page.locator("#updatingButton")
    before = upd.inner_text()

    page.evaluate(
        """() => {
            const el = document.getElementById('newButtonName');
            el.value = 'OnlyInput';
            el.dispatchEvent(new Event('input', {bubbles: true}));
        }"""
    )
    upd.click()

    assert upd.inner_text() == before, "只触发 input 时按钮不应更新"


def test_text_input_normal_flow_updates(page):
    """fill 会同时触发 input 与 change，按钮正常更新。"""
    page.goto(f"{BASE}/textinput")
    page.locator("#newButtonName").fill("MyButton")
    page.locator("#updatingButton").click()

    expect(page.locator("#updatingButton")).to_have_text("MyButton")


# ----------------------------------------------------------------------
# 场景 4/5：AJAX 长延迟 + 结果累积
# ----------------------------------------------------------------------

def test_ajax_long_delay_and_result_accumulation(page):
    """
    验证两点：
      1. 长延迟场景必须显式轮询等待（源码确认后端延迟固定约 15 秒）
      2. 多次触发时结果【累积】而非覆盖（源码为 appendChild，属页面缺陷）
    """
    page.goto(f"{BASE}/ajax")

    page.click("#ajaxButton")
    first = page.locator(".bg-success").first
    expect(first).to_have_text("Data loaded with AJAX get request.", timeout=90_000)

    page.click("#ajaxButton")
    page.wait_for_function(
        "document.querySelectorAll('.bg-success').length === 2", timeout=90_000
    )

    assert page.locator(".bg-success").count() == 2, \
        "结果应累积而非覆盖 —— 已知页面缺陷（appendChild 未清理）"


# ----------------------------------------------------------------------
# 场景 6：Progress Bar —— 随机速度下精确停止
# ----------------------------------------------------------------------

def test_progress_bar_stop_and_result_formula(page):
    """
    进度条的步进间隔为随机值（源码 `delay = Math.floor(random/2)`，0~499ms/步），
    因此无法用固定等待，必须在【浏览器内部】轮询。

    页面 Scenario 规定「停在 75% 附近，差值越小成绩越好」，
    实测 Result 显示值 = 停止时的进度值 - 75。
    """
    page.goto(f"{BASE}/progressbar")
    bar = page.locator("#progressBar")

    page.click("#startButton")
    page.wait_for_function(
        "parseInt(document.querySelector('#progressBar').getAttribute('aria-valuenow')) >= 75",
        polling=10,
        timeout=90_000,
    )
    page.click("#stopButton")
    page.wait_for_timeout(300)

    stopped = int(bar.get_attribute("aria-valuenow"))
    result_text = page.locator("#result").inner_text()

    # Result = 停止值 - 75 —— 这一条是确定的，可稳定断言
    assert f"Result: {stopped - 75}" in result_text, \
        f"停在 {stopped}% 时应显示 Result: {stopped - 75}，实际 {result_text!r}"


def test_progress_bar_reads_aria_valuenow(page):
    """进度值应通过 aria-valuenow 属性读取，而不是解析展示文本。"""
    page.goto(f"{BASE}/progressbar")
    bar = page.locator("#progressBar")

    value = bar.get_attribute("aria-valuenow")
    assert value is not None and value.isdigit(), \
        "aria-valuenow 应可直接作为数字使用，无需解析百分号"
