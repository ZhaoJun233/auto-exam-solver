---
name: auto-exam-solver
description: 通用在线考试/作业自动答题助手。支持各类教育平台（智慧职教、超星、学堂在线等），自适应 Vue/React/原生 HTML。处理验证码绕过、题目提取、答案选择与提交。
version: 2.1.0
scripts:
  - auto_exam_solver/browser_setup.py   # 浏览器接入：关闭/重启 Chrome、复制 profile、导出 Cookie
  - auto_exam_solver/page_prober.py     # 页面侦查：框架识别、题目提取、UI 选择器映射
  - auto_exam_solver/solver.py          # 主引擎：CLI 入口，连接浏览器 → 侦查 → 答题 → 提交
triggers:
  - 用户提到"答题"、"作业"、"考试"、"测验"、"自动作答"、"帮我做"
  - 用户分享在线教育平台的作业/考试页面 URL
  - 页面包含题目内容且用户要求作答
---

# ⛔ 核心原则：禁止使用 MCP 操作考试页面

**绝对不要使用 MCP chrome_devtools 系列工具操作考试/作业页面。** MCP 工具会引入独立的浏览器会话或自动化标志，触发教育平台的验证码/反作弊检测，导致：

- 滑块验证码反复弹出无法通过
- 平台检测到自动化行为并封禁账号
- 操作超时或页面状态不一致

## 唯一正确的方式：Playwright CDP 连接用户真实浏览器

本项目的全部页面交互必须通过 **Playwright CDP** 完成：

```
用户日常 Chrome ──(CDP 9222端口)──> Playwright ──> Python 脚本
```

这等价于在用户已登录、已解锁的浏览器中直接执行 JavaScript，**不引入任何自动化标志**。

## 操作分工

| 操作类型 | 正确工具 | 禁止工具 |
|---------|---------|---------|
| 启动/管理浏览器 | auto-exam-browser CLI | — |
| 页面探测、题目提取 | auto-exam-solver Python 脚本 | MCP snapshot/evaluate |
| 点击选项、翻页、提交 | auto-exam-solver Python 脚本 | MCP click/fill/navigate |
| 打开新标签页查看其他网站 | MCP navigate_page（非考试页） | — |
| 截图辅助调试 | MCP take_screenshot（仅调试用） | MCP take_snapshot |

## 执行流程

1. 告诉用户运行 auto-exam-browser start 启动调试模式 Chrome
2. 用户在浏览器中手动登录平台、进入考试页面、完成验证码（如有）
3. 运行 auto-exam-solver --cdp http://localhost:9222 --interactive 开始答题
4. 如果遇到 auto 模式无法给用户答题的情况，请改为手动模式（`--interactive`）
5. **全程通过 Python 脚本的 Playwright CDP 操控浏览器，不经过 MCP**

## 如果用户在 Codex 中触发此 skill

当用户说"帮我答题"、"自动做作业"等触发此 skill 时：
- **不要**尝试用 MCP 工具读取页面、点击元素或填写表单
- **应该**调用 Python 脚本（auto-exam-solver CLI 或 auto_exam_solver 模块）完成所有浏览器操作
- 如果需要查看页面状态，用 auto-exam-solver --probe-only 而不是 MCP snapshot
- 如果 auto 模式无法给用户答题，请改为手动模式（`--interactive`）

---


# 通用在线考试自动答题

## 安装说明（给 AI 助手看）

本项目是一个 skill 插件，需要被安装到设备的**全局 agent 配置目录**（而非本项目目录）才能被平台跨项目识别。

### Skill 文件的格式要求

Skill 不是单文件，必须遵循 **目录 + SKILL.md** 结构：

```
<skill名称>/
└── SKILL.md    # 文件名必须是 SKILL.md
```

本项目源文件位于 `.claude/skills/auto-exam-solver/SKILL.md`，安装时要把整个 `auto-exam-solver/` 目录拷贝到全局位置，确保目录下的文件名叫 `SKILL.md`（不是其他名字）。

### 让平台识别 skill

- **Claude Code**：有两种方式——
  - *推荐*：将 `auto-exam-solver/` 目录拷贝到 `~/.agents/skills/`，然后在 `~/.claude/skills/` 下创建符号链接指向它：`ln -s ~/.agents/skills/auto-exam-solver ~/.claude/skills/auto-exam-solver`
  - *备选*：直接将 `auto-exam-solver/` 目录拷贝到 `~/.claude/skills/` 下
  - 无论哪种方式，结果都是 `~/.claude/skills/auto-exam-solver/SKILL.md` 这个路径。Claude Code 启动时自动加载此目录下的所有 skill，跨项目生效。
- **Codex（OpenAI Codex CLI）**：将 `auto-exam-solver/` 目录拷贝到 Codex 在本设备上的全局 skills 路径（通常为 `~/.config/codex/skills/`），确保 `SKILL.md` 在目录内。
- **其他 AI 编程平台**：原理相同——到该平台在此设备上的全局 skills/agent 配置目录下，创建 `<skill名称>/SKILL.md` 的目录结构。

> 本项目自带的 `.claude/skills/auto-exam-solver/` 是 skill 的源目录。安装时从这里**拷贝**到全局位置。如果全局位置已有同名 skill 且版本更新，跳过此步。

### 让脚本能跑

skill 依赖三个 Python 脚本和两个第三方库（playwright、websocket-client），还需要 playwright 下载 Chromium 浏览器。先把本项目的 Python 包以开发模式安装到系统：`pip install -e .`（在项目根目录执行），这样 skill 引用的脚本就能在任意路径被调用。然后检查 Python 依赖和 Chromium 浏览器是否就绪，缺啥装啥。

### 验证

装完跑一下 `auto-exam-browser` 有输出，然后在平台触发 skill（如说"帮我答题"），能唤起就成功了。

**运行方式**：

- 方式 A — 命令行工具（推荐）：`auto-exam-browser start` 启动浏览器，`auto-exam-solver --interactive` 开始答题
- 方式 B — Python 模块：`python -m auto_exam_solver browser start` 和 `python -m auto_exam_solver solver --interactive`
- 方式 C — Python API：`from auto_exam_solver import probe_page, extract_questions, solve_exam`

## 适用场景
各类在线教育平台的作业/测验/考试自动作答，包括但不限于：智慧职教(icve)、超星学习通、学堂在线、中国大学MOOC、蓝墨云班课等。

## 工作流程

### Phase 1: 浏览器接入

**目标**：获得一个已登录目标平台的浏览器控制权。

**方案 A — CDP 直连（推荐，无 webdriver 检测）**：
```bash
# 使用 auto-exam-browser 命令
auto-exam-browser start

# 或使用 Python 模块
python -m auto_exam_solver browser start
```

等价于：
- 关闭 Chrome
- 复制 profile（保留 Cookie/Storage）到 `C:\Temp\chrome-debug-profile`
- 带 `--remote-debugging-port=9222` 重启 Chrome

**方案 B — 新建浏览器注入 Cookie（备选）**：
```bash
# 先从 CDP 浏览器导出 Cookie
auto-exam-browser cookies > cookies.json

# 用 Cookie 文件新建浏览器
auto-exam-solver --cookies cookies.json --url "https://xxx.com/exam/123"
```

**方案 C — 用户手动绕过验证码**：
当平台有滑块/图形验证码时，让用户在其日常浏览器中手动完成一次验证码。随后通过方案 A 或 B 接管浏览器，直接操作已解锁页面。

**选择逻辑**：优先 A（无 webdriver flag），若 profile 复制失败则用 B，若验证码持续弹窗则让用户手动解锁后用 A/B。

### Phase 2: 页面侦查

按以下顺序依次探测，直到获得足够信息：

**2.1 URL 分析**
```
- 提取路径段：courseId, examId, homeworkId 等参数
- 识别平台路由模式：hash vs history, RESTful vs query string
```

**2.2 框架识别**
```js
// 检测前端框架
const framework = {
  vue2: !!document.querySelector('#app').__vue__,
  vue3: !!document.querySelector('#app').__vue_app__,
  react: !!document.querySelector('[data-reactroot]') || !!window.__REACT_DEVTOOLS_GLOBAL_HOOK__,
  angular: !!document.querySelector('[ng-version]') || !!window.angular,
  jquery: !!window.jQuery,
  vanilla: false // fallback
};
```

**2.3 UI 组件库识别**
```
- iView/ViewUI → .ivu-*, .ivu-radio-input
- Element UI → .el-*, .el-radio__input
- Ant Design → .ant-*, .ant-radio-input
- Bootstrap → .form-check-input, .btn-primary
- 原生 HTML → input[type="radio"], input[type="checkbox"]
```

**2.4 题目数据源探测（按可靠性排序）**
```
1. Vue: root.__vue__ → 递归遍历 $children → 查找含 question/topic/exam 关键词的数组
2. React: __reactFiber$ / __reactInternalInstance$ → stateNode.memoizedState
3. DOM 直接解析: document.querySelectorAll('[class*="question"], [class*="topic"]')
4. 网络抓包: CDP Network.enable → 监听 XHR/fetch → 找 JSON 响应中含题目数据的
5. 页面文本: document.body.innerText（最后手段）
```

### Phase 3: 题目解析

**通用题目结构提取**：
```js
// 无论平台，题目都有一个通用 Schema
{
  id: string,           // 题目唯一ID
  type: 'single'|'multi'|'judge'|'fill'|'essay',  // 题型
  title: string,        // 题干
  options: [{           // 选项列表
    label: 'A',         // 选项标签
    content: string,    // 选项内容
    isAnswer: bool      // 是否为正确答案（初始为 false）
  }],
  score: number         // 分值
}
```

### Phase 4: 答案选择

**UI 交互适配器**：根据 Phase 2 识别的组件库选择正确的点击目标。

```
iView:      .ivu-radio-wrapper → .ivu-radio-input
Element:    .el-radio → .el-radio__original  
Ant Design: .ant-radio → .ant-radio-input
Bootstrap:  .form-check-input (原生 input)
原生:       input[type="radio"], input[type="checkbox"]
```

### Phase 5: 提交

1. 找到提交按钮（关键词匹配：`交卷|提交|submit|确认交卷|确认提交`）
2. 点击后等待弹窗确认
3. 弹窗中点击"确认"/"确定"/"是"
4. 等待结果页面加载
5. 验证提交状态

### Phase 6: 答案知识库

- **DHCP**：租约文件 `/var/lib/dhcpd`，自动分配 IP 的协议是 DHCP，端口 67/68
- **DNS**：端口 53，正向/反向解析，/etc/resolv.conf
- **Linux 权限**：chmod 数字模式，rwx = 4+2+1
- **Shell**：#!/bin/bash，$? 退出码，$# 参数个数

## 平台适配参考

### 智慧职教 (icve.com.cn)
- 框架: Vue 2 + iView
- 题目数据: `vm.$data.tmActivelist[]`
- 导航: `.topic-zpx-main span`（答题卡）
- Radio: `.ivu-radio-input`
- 验证码: 腾讯滑块 → 用户手动一次后 CDP 操作
- 作业列表: `/work` 路由，`getCellList` API

### 通用适配指引
遇到新平台时，按 Phase 2→3→4→5 顺序探测，记录：
- 前端框架 + UI 库
- 题目数据的 Vue/React/DOM 路径
- 题型渲染的 HTML 结构
- 导航和提交的按钮选择器

## 风险提示
- 仅用于合法学习场景：自测、复习、补交
- 不要在正式考试/证书考试中使用
- 不同平台有不同反作弊机制，CDP 模式比 `chromium.launch()` 更难检测
- 频繁操作可能触发平台限流，每题之间等待 1-2 秒


## 验证码处理策略

当页面检测到验证码时（腾讯滑块、极验、图形验证码等），本工具会自动暂停并提示用户手动处理。具体流程：

1. 答题过程中自动检测验证码弹窗
2. 检测到后暂停自动操作，打印提示信息
3. 用户在浏览器中手动完成验证码
4. 用户在终端按回车继续
5. 工具自动恢复答题流程

**重要**：验证码的触发频率与操作方式直接相关。使用 Playwright CDP 操作用户真实浏览器（无 webdriver 标志）时，验证码触发率远低于 MCP 工具或 Selenium。
