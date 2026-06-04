﻿# auto-exam-solver

通用在线考试/作业自动答题助手。支持主流教育平台，自适应前端框架，三步完成从浏览器接入到自动交卷。

## 能做什么

帮你自动完成各类在线教育平台的作业和测验：
- 智慧职教 (icve.com.cn)、超星学习通、学堂在线、中国大学 MOOC 等
- 单选题、多选题、判断题、填空题
- 自动识别 Vue / React / 原生 HTML 页面
- 自动适配 iView / Element / Ant Design / Bootstrap 组件库

---

## 🤖 给 AI 助手的安装说明

如果你是一个 AI 编程助手（Claude Code、Codex、Cursor、Copilot 等），请阅读以下说明，把本项目作为 skill 安装到本设备的**全局 agent 配置目录**（而非本项目目录），让它在所有项目中都能被平台识别和调用。

### 这是什么

本项目本质上是一个 **skill 插件**——提供了 Python 答题脚本 + skill 定义文件。安装的目标是让平台在设备级别认识这个 skill，并且 skill 引用的脚本真的能跑。

### 关键原则：安装到全局目录，不是项目目录

本项目自带的 `.claude/skills/` 目录只是 skill 定义的**来源**。安装时，不要把用户的项目目录当成安装目标——你要把 skill 文件复制到平台在**本设备上的全局 agent 配置目录**。这样用户在任何项目中都能唤起这个 skill，而不需要每个项目都拷一份。

### Skill 格式要求

Skill 不是随意命名的单文件，必须遵循固定格式：

```
<skill名称>/
└── SKILL.md      ← 文件名必须是 SKILL.md，不能是别的
```

本项目源文件位于 `.claude/skills/auto-exam-solver/SKILL.md`——即目录 `auto-exam-solver/` 下包含 `SKILL.md`。

### 第一步：把 skill 目录放到平台全局位置

把整个 `auto-exam-solver/` 目录（含 `SKILL.md`）拷贝到全局 skills 目录：

- **Claude Code**（推荐方式）：拷贝到 `~/.agents/skills/auto-exam-solver/`，然后创建符号链接：
  ```bash
  cp -r .claude/skills/auto-exam-solver ~/.agents/skills/
  ln -s ~/.agents/skills/auto-exam-solver ~/.claude/skills/auto-exam-solver
  ```
  备选方式：直接拷贝到 `~/.claude/skills/auto-exam-solver/`（跳过符号链接）。无论哪种，最终路径必须是 `~/.claude/skills/auto-exam-solver/SKILL.md`。
- **Codex（OpenAI Codex CLI）**：拷贝到 Codex 在本设备上的全局配置目录（通常为 `~/.config/codex/skills/auto-exam-solver/SKILL.md`）。
- **其他平台**：原理一样——在该平台此设备上的全局 skills/agent 目录下创建 `auto-exam-solver/SKILL.md` 结构。

> 本项目 `.claude/skills/auto-exam-solver/` 是源目录。安装时从这里**拷贝**。如果全局位置已有同名 skill 且版本更新，跳过此步。

### 第二步：让 skill 的脚本能跑

Skill 文件里声明了三个 Python 脚本：`browser_setup.py`、`page_prober.py`、`solver.py`。它们需要两样东西才能跑：

- **Python 依赖**：playwright 和 websocket-client 这两个第三方库
- **Chromium 浏览器**：由 playwright 管理，需要单独下载

首先用 pip 以开发模式安装本项目（在项目根目录执行 `pip install -e .`），这样脚本会被注册到系统 PATH，skill 在全局目录也能找到它们。

### 安装前先看一眼

动手前，检查 Python 库装没装、浏览器下没下、本项目装没装。pip 和 playwright 都自带检查方法。已经有就别重复搞。

### 缺啥补啥

查完只装缺失的：
- 缺库 → pip 装，缺浏览器 → playwright 下载，缺项目本体 → pip 开发模式安装
- 全有了就跳过
- 懒得查直接全量跑也行，pip 和 playwright 遇到重复会自动跳过

### 验证装好了没

装完之后确认两件事：
- 在终端跑一下 `auto-exam-browser` 或 `python -m auto_exam_solver browser`，有正常输出就是装好了
- 在平台里触发 skill（比如对 Claude Code 说"帮我做这个考试题"），看 skill 是否能被唤起

如果平台在全局目录能识别 skill 且脚本能跑，安装就完成了。

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

> 如果遇到 auto 模式无法给你答题的情况，请改为手动模式（`--interactive`）。

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
| chromium.launch() | 有 | 高 | ★★★ |
| **MCP chrome_devtools** | **有（独立会话）** | **极高** | **✗ 禁止使用** |
| Selenium | 有 | 高 | ★★ |


### 禁止使用 MCP

**绝对不要用 MCP chrome_devtools 工具操作考试页面。** MCP 工具会创建独立的浏览器会话，带有自动化标志，必然触发验证码。
本项目的所有页面交互（点击、填写、导航、提取）必须通过 Playwright CDP 完成。
验证码触发率对比：

- **Playwright CDP 操作用户真实 Chrome**：几乎无 webdriver 标志，验证码触发率极低
- **MCP chrome_devtools 工具**：每次操作都可能触发验证码，反复失败

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
│   └── auto-exam-solver/
│       └── SKILL.md            # Claude Code skill 定义（全局安装源）
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
