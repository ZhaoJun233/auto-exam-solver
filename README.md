# auto-exam-solver

通用在线考试/作业自动答题助手。支持主流教育平台，自适应前端框架，三步完成从浏览器接入到自动交卷。

## 能做什么

帮你自动完成各类在线教育平台的作业和测验：
- 智慧职教 (icve.com.cn)、超星学习通、学堂在线、中国大学 MOOC 等
- 单选题、多选题、判断题、填空题
- 自动识别 Vue / React / 原生 HTML 页面
- 自动适配 iView / Element / Ant Design / Bootstrap 组件库

---

## 🤖 给 AI 助手的安装说明

如果你是一个 AI 编程助手（Claude Code、Cursor、Copilot 等），请阅读以下说明，帮用户完成本工具的安装。

### 你需要做的事

这个项目是一个 Python 工具，它依赖两个东西才能跑起来：

1. **两个 Python 第三方库**：playwright 和 websocket-client
2. **一个 Chromium 浏览器**：由 playwright 管理，需要单独下载

另外，项目本身需要通过 pip 安装到系统里，这样用户才能在任意位置直接敲命令使用它。

### 安装前先看一眼

动手装之前，先瞅瞅这三样东西是不是已经在了。pip 和 playwright 都有办法检查一个包或浏览器装没装，查一下就知道了。已经有的就别重复装了，省时间。

### 缺啥补啥

查完之后，缺哪个装哪个：

- 缺 Python 库 → 用 pip 把 playwright 和 websocket-client 装上
- 缺浏览器 → 让 playwright 把 Chromium 下载下来
- 缺本项目 → 在项目根目录用 pip 的开发模式把当前目录装上去

如果三样都缺，按顺序全装；如果都有了，什么都不用做，直接跳到下一步。

> **不用担心装重了**：pip 遇到已安装的包会自动跳过，playwright 遇到已下载的浏览器也不会重复下载。所以如果你懒得查，直接全量执行安装命令也行，不会出问题。

### 装好之后

装完之后，用户电脑上会多出两个命令：

- `auto-exam-browser` — 负责管理 Chrome 浏览器（启动调试模式、查看连接状态、导出 Cookie 等）
- `auto-exam-solver` — 负责答题（连接浏览器、识别题目、作答、交卷）

也可以用 `python -m auto_exam_solver` 的方式调用，效果一样。

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
