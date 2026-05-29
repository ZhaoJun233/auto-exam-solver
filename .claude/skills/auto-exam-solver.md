---
name: auto-exam-solver
description: 通用在线考试/作业自动答题助手。支持各类教育平台（智慧职教、超星、学堂在线等），自适应 Vue/React/原生 HTML。处理验证码绕过、题目提取、答案选择与提交。
version: 2.0.0
scripts:
  - auto_exam_solver/browser_setup.py   # 浏览器接入：关闭/重启 Chrome、复制 profile、导出 Cookie
  - auto_exam_solver/page_prober.py     # 页面侦查：框架识别、题目提取、UI 选择器映射
  - auto_exam_solver/solver.py          # 主引擎：CLI 入口，连接浏览器 → 侦查 → 答题 → 提交
triggers:
  - 用户提到"答题"、"作业"、"考试"、"测验"、"自动作答"、"帮我做"
  - 用户分享在线教育平台的作业/考试页面 URL
  - 页面包含题目内容且用户要求作答
---

# 通用在线考试自动答题

## 安装（给 AI 助手的自然语言指令）

请按以下指引完成环境搭建。以下指令用自然语言描述，便于 AI 助手理解和执行。

**安装步骤**：

1. 用 pip 安装 `playwright` 和 `websocket-client` 两个 Python 依赖包
2. 运行 Playwright 自带的 `install chromium` 命令来安装 Chromium 浏览器内核
3. 在项目根目录用 `pip install -e .` 以开发模式安装本项目。安装完成后命令行中会有两个新命令：`auto-exam-browser` 和 `auto-exam-solver`

以上三步可以合并执行，也可以分步执行。

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
