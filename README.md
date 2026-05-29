# auto-exam-solver

通用在线考试/作业自动答题助手。支持主流教育平台，自适应前端框架，三步完成从浏览器接入到自动交卷。

## 能做什么

帮你自动完成各类在线教育平台的作业和测验：
- 智慧职教 (icve.com.cn)、超星学习通、学堂在线、中国大学 MOOC 等
- 单选题、多选题、判断题、填空题
- 自动识别 Vue / React / 原生 HTML 页面
- 自动适配 iView / Element / Ant Design / Bootstrap 组件库

---

## 🤖 Agent 一键安装（给 AI 助手的自然语言指令）

如果你是一个 AI 编程助手（如 Claude Code、Cursor、Copilot 等），请阅读以下指令并自动完成安装。这些指令用自然语言写成，方便你理解和执行。

### 安装指令

请在项目根目录完成以下环境检测和安装。**先检查已有环境，再决定需要执行哪些步骤，避免重复安装。**

**第 0 步 — 环境检测（必做）**

在安装前，先检查以下三项是否已经就绪：

- 检查 Python 依赖：运行 `pip show playwright` 和 `pip show websocket-client`，如果两者都显示版本信息，说明依赖已安装
- 检查浏览器内核：运行 `playwright install --dry-run chromium` 或检查 Chromium 浏览器二进制是否已存在，如果已安装则跳过
- 检查本项目：运行 `pip show auto-exam-solver`，如果显示版本信息（2.0.0），说明本项目已安装

根据检测结果，仅执行缺失的步骤。

**第 1 步 — 安装 Python 依赖（仅当缺失时）**

如果上一步检测到 `playwright` 或 `websocket-client` 未安装，用 pip 安装这两个包。已安装的包会自动跳过，所以也可以直接执行 `pip install playwright websocket-client`，pip 会智能处理。

**第 2 步 — 安装浏览器内核（仅当缺失时）**

如果检测到 Chromium 浏览器尚未安装，运行 `playwright install chromium`。如果已存在则跳过此步。

**第 3 步 — 安装本项目（仅当缺失时）**

如果 `pip show auto-exam-solver` 未显示版本信息，在项目根目录执行 `pip install -e .` 以开发模式安装。安装完成后 `auto-exam-solver` 和 `auto-exam-browser` 两个命令即可在任意路径下使用。

**总结**

以上三步的理想执行路径：
- 全新环境：依次执行依赖安装 → 浏览器安装 → 项目安装
- 依赖已就绪、项目未装：只需执行 `pip install -e .`
- 全部已就绪：无需任何安装，直接使用 `auto-exam-browser` 和 `auto-exam-solver` 命令
- 不确定时：直接执行 `pip install playwright websocket-client && playwright install chromium && pip install -e .`，pip 和 Playwright 会自动跳过已满足的部分

### 可用的命令行工具

安装完成后，系统中会多出两个全局命令：

- `auto-exam-browser` — 浏览器管理工具，子命令包括：
  - `start`：关闭当前 Chrome 并带调试端口重启（端口 9222）
  - `connect`：检查 CDP 连接状态，列出已打开的页面
  - `cookies`：导出浏览器 Cookie 为 JSON 格式
  - `restart`：仅重启 Chrome，不重新复制用户配置

- `auto-exam-solver` — 答题引擎，主要参数：
  - `--cdp http://localhost:9222` 指定 Chrome DevTools Protocol 连接地址
  - `--url <考试页面URL>` 直接打开目标考试页面
  - `--interactive` 开启交互模式，逐题询问答案
  - `--probe-only` 仅侦查页面结构，不实际答题
  - `--questions-file result.json` 将提取到的题目保存为 JSON 文件
  - `--cookies cookies.json` 使用已保存的 Cookie 文件新建浏览器会话

也可以用 `python -m auto_exam_solver solver` 和 `python -m auto_exam_solver browser` 通过模块方式调用。

### Agent 作为 Python 库调用

如果需要更灵活的控制，可以直接 import 本包的核心 API：

```python
import asyncio
from auto_exam_solver import probe_page, extract_questions, solve_exam

# 连接 CDP 浏览器 → 侦查页面 → 提取题目 → 作答
async def auto_solve():
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp("http://localhost:9222")
        page = browser.contexts[0].pages[0]
        info = await probe_page(page)
        questions = await extract_questions(page, info.framework)
        await solve_exam(page, questions, info, interactive=True)

asyncio.run(auto_solve())
```

---

## 快速开始（人类版）

### 环境要求

```bash
# 一键安装所有依赖
pip install playwright websocket-client && playwright install chromium && pip install -e .
```

### 三步完成答题

**第 1 步：启动浏览器**

在你日常使用的 Chrome 中登录目标平台，然后：

```bash
auto-exam-browser start
```

这行命令会关闭 Chrome、复制你的登录状态、然后用调试模式重新打开。你的所有标签页和登录状态都会保留。

**第 2 步：打开考试页面**

在浏览器中导航到作业/考试页面，手动完成验证码（如果有的话）。

**第 3 步：运行答题引擎**

```bash
auto-exam-solver --interactive
```

引擎会：
1. 自动识别页面框架和组件库
2. 提取所有题目和选项
3. 逐题询问你正确答案（输入 A/B/C/D）
4. 自动点击选项、翻页、提交

## 命令参考

### auto-exam-browser — 浏览器管理

| 命令 | 功能 |
|------|------|
| `auto-exam-browser start` | 关闭 Chrome → 复制登录状态 → 调试模式重启 |
| `auto-exam-browser connect` | 检查连接状态，列出所有打开的页面 |
| `auto-exam-browser cookies` | 导出 Cookie 为 JSON（用于其他电脑） |
| `auto-exam-browser restart` | 仅重启 Chrome（不重新复制 profile） |

### auto-exam-solver — 答题引擎

| 参数 | 功能 |
|------|------|
| `--cdp http://localhost:9222` | 连接已有 Chrome（默认） |
| `--url <考试页面URL>` | 直接打开考试页面 |
| `--interactive` | 每题询问答案后作答 |
| `--probe-only` | 仅分析页面，不答题 |
| `--questions-file result.json` | 将题目导出为 JSON |
| `--cookies cookies.json` | 用 JSON Cookie 新建浏览器 |

## 工作原理

```
你的浏览器 ──(CDP)──> Playwright ──> Python
                         │
                    页面侦查模块
                    ├── 检测框架: Vue2/3 | React | 原生
                    ├── 检测组件库: iView | Element | Antd
                    └── 检测导航: 答题卡 | 翻页 | 滚动
                         │
                    题目提取模块
                    ├── 策略1: Vue.__vue__.$data 直接读取
                    ├── 策略2: React fiber 树遍历
                    └── 策略3: DOM HTML 解析
                         │
                    作答模块
                    ├── 匹配正确的 radio/checkbox 选择器
                    ├── 逐题导航、点击选项
                    └── 交卷 + 确认弹窗
```

## 为什么用 CDP 而不是直接自动化

| 方式 | webdriver 检测 | 验证码触发 | 推荐度 |
|------|:---:|:---:|:---:|
| CDP 连接日常 Chrome | 无 | 低 | ★★★★★ |
| `chromium.launch()` | 有 | 高 | ★★★ |
| Selenium | 有 | 高 | ★★ |

CDP 模式连接的是你正常使用的 Chrome 浏览器，没有自动化标志，平台无法检测。

## 项目结构

```
auto-exam-solver/
├── auto_exam_solver/           # Python 包（可供 pip install + import）
│   ├── __init__.py             # 公开 API：probe_page, extract_questions, solve_exam
│   ├── __main__.py             # python -m auto_exam_solver 入口
│   ├── browser_setup.py        # 浏览器接入（关闭/重启/复制profile/Cookie导出）
│   ├── page_prober.py          # 页面侦查（框架识别/题目提取/选择器映射）
│   └── solver.py               # 主引擎（CLI入口，完整答题流程）
├── .claude/skills/
│   └── auto-exam-solver.md     # Claude Code skill 定义
├── pyproject.toml              # pip install 配置
├── requirements.txt            # Python 依赖
├── .gitignore
└── README.md
```

## 常见问题

**Q: 验证码怎么处理？**
A: 在你自己的浏览器中手动完成一次验证码。之后 CDP 浏览器可以直接操作已解锁的页面。

**Q: 支持主观题吗？**
A: 当前版本仅支持选择题（单选/多选/判断）。主观题会跳过。

**Q: 遇到新平台怎么办？**
A: 引擎会自动探测页面结构。如果是全新框架，会回退到 DOM 解析模式。你也可以提 Issue 附带平台 URL。

**Q: 会被平台检测出来吗？**
A: CDP 模式使用的是你的真实浏览器，没有 `navigator.webdriver` 标志。每道题之间自动等待 1-2 秒，模拟正常答题节奏。

## 免责声明

本工具仅供合法学习场景使用：自测、复习、补交作业。请勿用于正式考试、证书考试、或任何违反学校/平台规定的场景。使用者自行承担违规后果。
