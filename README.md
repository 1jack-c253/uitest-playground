# UI Test Automation Playground 自动化测试

[![UI Tests](https://github.com/1jack-c253/uitest-playground/actions/workflows/ui-tests.yml/badge.svg)](https://github.com/1jack-c253/uitest-playground/actions/workflows/ui-tests.yml)

对公开练习靶场 [uitestingplayground.com](http://uitestingplayground.com) 中 **6 个「抗自动化」场景**做测试设计与执行。

测试套件由 **GitHub Actions 持续集成**：每次 push / PR 自动在 Ubuntu 环境安装
Playwright 并执行全部用例，构建产物包含 junit 测试报告。

这个靶场把真实项目里最难自动化的场景单独做成了页面 —— 动态元素、异步长延迟、防脚本点击、事件依赖等。
本项目对其中 6 个场景做了完整测试，并记录了每一个自动化难题的**定位过程与解决方式**。

---

## 一、6 个场景与自动化要点

| 场景 | 页面机制 | 自动化要点 |
|---|---|---|
| **Dynamic ID** | 按钮 id 为随机 UUID，每次刷新都变 | 禁用 id 定位，改用文本 / class / 相对 XPath |
| **AJAX Data** | 点击后请求服务端，约 15.6 秒返回 | 必须显式轮询等待 |
| **Client Side Delay** | 点击后客户端 `setTimeout(…, 15000)`（源码写死 15 秒） | 必须显式轮询等待 |
| **Click** | 按钮忽略 DOM 合成点击，仅认带真实屏幕坐标的鼠标事件 | 用真实输入通道，不用 `dispatchEvent` |
| **Text Input** | 要求 `input` 与 `change` 两事件的值一致才更新按钮 | 模拟完整用户输入，不能只触发单个事件 |
| **Progress Bar** | 点 Start 后随机速度递增至 100%，需在 75% 附近精确停止 | 浏览器内轮询 + 读 `aria-valuenow` |

---

## 二、三个关键发现

### 1. Click 场景的判据是 `screenX`，不是 `isTrusted`

页面源码：

```javascript
function ClickEventHandler(event) {
    if (event.target.id == "badButton") {
        if (event.screenX > 0) {                            // ← 唯一判据
            event.target.className = 'btn btn-success';
        }
    }
}
```

**对照实验**（用事件探针读取处理器实际收到的参数）：

| 点击方式 | 按钮 | 探针读到 screenX | isTrusted |
|---|---|---|---|
| `dispatch_event('click')` | 未变 | **0** | False |
| JS 原生 `element.click()` | 未变 | **0** | False |
| Playwright `locator.click()` | **变绿** | 247 | True |
| `mouse.move` + `down` + `up` | **变绿** | 247 | True |
| **合成事件 + 手动填 screenX = 95** | **变绿** | 95 | **False** |

最后一行是决定性证据：一个 `isTrusted = False` 的**纯合成事件**，仅因 `screenX > 0`
就让按钮变绿 —— **判据是 `screenX`，与 `isTrusted` 无关**。

**附带发现**：Playwright 的 mouse API **不移动操作系统真实光标**。
用 Windows API 读系统光标坐标，点击前后完全不变，但按钮照样变绿 ——
它是通过 CDP 将输入事件注入浏览器输入管线，并非模拟真实鼠标移动。

### 2. Chromium 后台标签页定时器节流

进度条场景在真实浏览器中切到后台后进度会停滞 —— Chromium 在页面不可见
（`document.visibilityState === 'hidden'`）时会对定时器节流以省电。

**但用 Playwright 跑时该现象不会出现**，实测 `chrome://version` 的命令行参数：

```
--disable-background-timer-throttling
--disable-backgrounding-occluded-windows
--disable-renderer-backgrounding
```

自动化框架为保证测试结果稳定，默认关闭了节流。

**这三个参数的存在本身即说明该现象真实存在** —— 没有人会写参数去禁用一个不存在的问题。
这也说明：**同一场景换不同工具执行，结果可能完全不同**，部分真实环境问题自动化无法覆盖。

### 3. 进度条的延迟是随机的，不是固定的

```javascript
function Start() {
    var random = "" + (new Date()).getTime();
    random = parseInt(random.substr(random.length - 3, 3));   // 时间戳后三位
    delay = Math.floor(random / 2);                           // → 0~499 毫秒/步
    ratio = 25;
    ...
}
```

每次点击 Start 会生成一个 **0~499 毫秒的随机步进间隔**，
因此从 25% 跑到 100% 的耗时在 **约 0.5 秒到 37 秒**之间浮动，相差近 100 倍。

**这就是固定超时必然失败的根本原因** —— 等待时长无法预估。
正确做法是**在浏览器内部轮询**（`page.wait_for_function`），
若在自己的代码里循环读取，每次读取都要与浏览器通信一次，等读到目标值时早已跑过。

### 4. `Result` 的含义与 `aria-valuenow` 的读取

页面 Scenario 要求「停在 75% 附近，差值越小成绩越好」。实测确认：

| 停止时的进度值 | 页面显示的 Result |
|---|---|
| 40 | `Result: -35, duration: 7192` |
| 60 | `Result: -15, duration: 3951` |
| 90 | `Result: 15, duration: 23145` |

**`Result` = 停止时的进度值 − 75。**

进度读取应使用 `aria-valuenow` 属性而非 `innerHTML` 文本 ——
属性值为纯数字可直接比较，且 `aria-` 属性为机器可读的语义标记，比展示文本更稳定。

---

## 三、发现的问题（分类）

按「**真实用户是否会遇到**」与「**是否为页面自身问题**」两个维度分类：

| 问题 | 用户会遇到 | 页面自身问题 | 分类 |
|---|---|---|---|
| 多次触发结果累积，不清理（源码为 `appendChild`） | ✅ | ✅ | **页面缺陷**（应可用 `innerHTML =` 覆盖） |
| `input`/`change` 单事件不更新按钮文案 | ❌ 键盘输入天然两个事件都触发 | —— | **自动化陷阱**（属测试方式问题，非页面缺陷） |
| 清空输入框后按钮不更新 | ✅ | ✅ | **页面缺陷**（源码 `if (NewButtonNameC && …)` 中空字符串被判定为假值） |
| 后台标签页定时器节流 | ✅ | ❌ 浏览器行为，非页面问题 | **环境限制**（开发无法修复，记入环境注意事项） |

> 区分这三类很重要：**页面缺陷**提给开发；**自动化陷阱**应改进测试代码而非提缺陷单；
> **环境限制**记录下来、测试时规避即可。

---

## 四、运行方式

```bash
pip install -r requirements.txt
playwright install chromium
```

### 运行测试套件（9 条用例）

```bash
pytest tests/ -v
```

本地实测：`9 passed in 60.94s`（headless 模式）

| 用例 | 验证点 |
|---|---|
| `test_dynamic_id_changes_on_reload` | 刷新后 id 变化，class / 文本稳定可作定位依据 |
| `test_click_synthetic_event_is_ignored` | JS 合成 click 被过滤（screenX = 0） |
| `test_click_real_mouse_event_works` | 带真实屏幕坐标的鼠标事件生效 |
| `test_click_judgement_is_screenx_not_istrusted` | 铁证：纯合成事件仅填 screenX 即可绕过 |
| `test_text_input_requires_both_events` | 只触发 input 不触发 change → 按钮不更新 |
| `test_text_input_normal_flow_updates` | 完整输入流程 → 按钮正常更新 |
| `test_ajax_long_delay_and_result_accumulation` | 显式轮询等待 + 结果累积缺陷验证 |
| `test_progress_bar_stop_and_result_formula` | 浏览器内轮询精确停止 + `Result = 停止值 − 75` |
| `test_progress_bar_reads_aria_valuenow` | 应读 aria 属性而非解析展示文本 |

### 交互式走查（6 个场景，逐个暂停讲解）

```bash
python walkthrough.py
```

按回车推进到下一站。若在无交互终端中运行，可加 `--auto` 自动推进：

```bash
python walkthrough.py --auto
PAUSE_SECONDS=20 python walkthrough.py --auto   # 自定义每站停留秒数
```

### 复现各场景

```bash
python probe/reproduce.py            # 7 个场景综合复现
python probe/click_definitive.py     # Click 场景 4 种点击方式对照
python probe/flags.py                # 读取浏览器启动参数中的节流开关
python probe/d1_proper.py            # 结果累积行为验证
python probe/progressbar_source.py   # 进度条源码 + Result 含义验证
python probe/shots.py                # 批量生成带标注的截图
```

> 提示：Windows 上若 `python` 命令被 Microsoft Store 存根占用，请使用 Python 的完整路径。

---

## 五、目录结构

```
.
├── walkthrough.py           # 交互式走查脚本（6 站）
├── tests/                   # pytest 测试套件（9 条用例，CI 自动执行）
├── screenshots/             # 14 张带标注的现场截图
└── probe/
    ├── recon.py             # 页面 DOM 结构侦察，获取准确选择器
    ├── reproduce.py         # 7 个场景综合复现
    ├── click_definitive.py  # Click 场景 4 种方式对照实验（含事件探针）
    ├── click_why.py         # 排除 slow_mo / viewport 等干扰变量
    ├── cursor_test.py       # 验证 Playwright 是否移动系统光标
    ├── flags.py             # 读取 chrome://version 对比启动参数
    ├── throttle*.py         # 后台节流三组对照实验
    ├── d1_proper.py         # 结果累积行为验证
    ├── d1_and_delay.py      # 延迟实测
    ├── read_source.py       # 批量读取页面 JavaScript 源码
    ├── textinput_source.py  # Text Input 页面源码
    ├── progressbar_source.py# Progress Bar 页面源码 + Result 含义
    └── shots.py             # 批量生成带标注截图
```

---

## 六、技术栈

- Python 3.13
- Playwright 1.62（Chromium，有头 / 无头模式）
- pytest 9.1.1

**测试环境**：Windows 11，物理分辨率 1920×1080，逻辑 1536×864（系统缩放 125%）
