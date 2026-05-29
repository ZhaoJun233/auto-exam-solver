"""
页面侦查与题目提取模块 — 识别前端框架、UI 库、提取题目数据。

Usage:
    from page_prober import probe_page, extract_questions
    from playwright.sync_api import Page

    info = probe_page(page)
    questions = extract_questions(page, info["framework"])
"""

from dataclasses import dataclass, field, asdict
from typing import Optional
import json


@dataclass
class Option:
    label: str           # A/B/C/D
    content: str         # 选项文本
    is_selected: bool = False
    is_correct: bool | None = None


@dataclass
class Question:
    id: str
    type: str            # single | multi | judge | fill | essay
    title: str           # 题干
    options: list[Option] = field(default_factory=list)
    score: float = 0
    index: int = 0       # 题号


@dataclass
class PageInfo:
    url: str
    title: str
    framework: str       # vue2 | vue3 | react | vanilla
    ui_library: str      # iview | element | antd | bootstrap | native
    navigation: str      # card(答题卡) | pager(翻页) | scroll(滚动) | page(分页)
    has_captcha: bool
    question_count: int


# ─── Framework Detection ────────────────────────────────────────────

FRAMEWORK_DETECT_JS = r"""
() => {
  const app = document.querySelector('#app, #root, [ng-app]');
  const results = { vue2: false, vue3: false, react: false, angular: false };

  // Vue 2
  if (app && app.__vue__) results.vue2 = true;
  // Vue 3
  if (app && (app.__vue_app__ || app._vnode)) results.vue3 = true;
  // React
  const rootEl = document.getElementById('root') || document.getElementById('app');
  if (rootEl) {
    const reactKey = Object.keys(rootEl).find(k =>
      k.startsWith('__reactFiber') || k.startsWith('__reactInternalInstance')
    );
    if (reactKey || window.__REACT_DEVTOOLS_GLOBAL_HOOK__) results.react = true;
  }
  // Angular
  if (document.querySelector('[ng-version]') || window.angular) results.angular = true;

  return results;
}
"""

UI_DETECT_JS = r"""
() => {
  const html = document.documentElement.innerHTML.substring(0, 50000);
  return {
    iview: html.includes('ivu-radio') || html.includes('ivu-btn') || html.includes('ivu-modal'),
    element: html.includes('el-radio') || html.includes('el-button') || html.includes('el-dialog'),
    antd: html.includes('ant-radio') || html.includes('ant-btn') || html.includes('ant-modal'),
    bootstrap: html.includes('form-check-input') || html.includes('btn-primary'),
  };
}
"""

NAVIGATION_DETECT_JS = r"""
() => {
  const html = document.body.innerText || '';

  if (html.includes('答题卡') || html.includes('題號')) return 'card';
  if (html.includes('上一题') && html.includes('下一题')) return 'pager';
  if (document.querySelectorAll('[class*="question"]').length > 3) return 'scroll';
  return 'page';
}
"""


# ─── Question Extraction ────────────────────────────────────────────

VUE_QUESTION_EXTRACT = r"""
() => {
  const root = document.querySelector('#app').__vue__;
  if (!root) return null;

  // 递归搜索含 question/topic/exam 数据的组件
  function findQuestions(vm, depth) {
    if (depth > 8 || !vm) return null;
    try {
      if (vm.$data) {
        for (const [key, val] of Object.entries(vm.$data)) {
          if (!Array.isArray(val) || val.length === 0 || val.length > 100) continue;
          const first = val[0];
          if (first && typeof first === 'object') {
            if (first.title || first.questionTitle || first.content || first.questionContent ||
                first.typeId || first.questionId || first.dataArr || first.options) {
              return { key, data: val };
            }
          }
        }
      }
    } catch(e) {}
    if (vm.$children) {
      for (const child of vm.$children) {
        const r = findQuestions(child, depth + 1);
        if (r) return r;
      }
    }
    return null;
  }

  return findQuestions(root, 0);
}
"""

REACT_QUESTION_EXTRACT = r"""
() => {
  // 从 React fiber 树中提取 state
  const rootEl = document.getElementById('root') || document.getElementById('app');
  if (!rootEl) return null;

  const fiberKey = Object.keys(rootEl).find(k =>
    k.startsWith('__reactFiber') || k.startsWith('__reactInternalInstance')
  );
  if (!fiberKey) return null;

  // 遍历 fiber 树找题目数据
  function walkFiber(fiber, depth) {
    if (depth > 30 || !fiber) return null;
    const state = fiber.memoizedState;
    if (state && state.queue) {
      const val = state.memoizedState || state.baseState;
      if (Array.isArray(val) && val.length > 0 && val.length <= 200) {
        const first = val[0];
        if (first && typeof first === 'object' && (first.title || first.content || first.options)) {
          return val;
        }
      }
    }
    const childResult = walkFiber(fiber.child, depth + 1);
    if (childResult) return childResult;
    return walkFiber(fiber.sibling, depth + 1);
  }

  return walkFiber(rootEl[fiberKey], 0);
}
"""

DOM_QUESTION_EXTRACT = r"""
() => {
  // 从 DOM 结构提取题目（最后手段）
  const questions = [];
  const containers = document.querySelectorAll(
    '[class*="question-item"], [class*="topic-item"], [class*="exam-item"], ' +
    '[class*="single"], [class*="multi"], [class*="judge"], ' +
    '.question, .topic, [data-question-id]'
  );
  if (containers.length === 0) return null;

  containers.forEach((el, i) => {
    const text = (el.textContent || '').trim();
    if (text.length < 10) return;

    // 提取题干
    const titleMatch = text.match(/(\d+)[、.][［\[](.+?)[］\]](.+?)(?=[A-Z][、.]|$)/s);
    const qType = titleMatch ? titleMatch[2] : 'single';
    const title = titleMatch ? titleMatch[3].trim() : text.substring(0, 100);

    // 提取选项
    const options = [];
    const optMatches = text.matchAll(/([A-Z])[、.]\s*(.+?)(?=\s*[A-Z][、.]|$)/g);
    for (const m of optMatches) {
      options.push({ label: m[1], content: m[2].trim() });
    }

    questions.push({
      id: el.getAttribute('data-question-id') || el.id || `dom-q-${i}`,
      type: qType.includes('多') ? 'multi' : qType.includes('判') ? 'judge' : 'single',
      title,
      options,
      score: 0,
      index: i + 1,
    });
  });

  return questions.length > 0 ? questions : null;
}
"""


# ─── Public API ─────────────────────────────────────────────────────

async def probe_page(page) -> PageInfo:
    """侦查页面：识别框架、UI 库、导航模式、验证码状况。"""
    fw = await page.evaluate(FRAMEWORK_DETECT_JS)
    ui = await page.evaluate(UI_DETECT_JS)
    nav = await page.evaluate(NAVIGATION_DETECT_JS)

    framework = (
        "vue2" if fw.get("vue2") else
        "vue3" if fw.get("vue3") else
        "react" if fw.get("react") else
        "angular" if fw.get("angular") else
        "vanilla"
    )

    ui_library = (
        "iview" if ui.get("iview") else
        "element" if ui.get("element") else
        "antd" if ui.get("antd") else
        "bootstrap" if ui.get("bootstrap") else
        "native"
    )

    body_text = await page.evaluate("() => document.body?.innerText || ''")
    has_captcha = any(kw in body_text for kw in
        ["安全验证", "拖动滑块", "拼图完成验证", "请完成安全验证", "captcha", "verify"]
    )

    # 尝试提取题目数量
    q_count = 0
    if framework == "vue2":
        raw = await page.evaluate(VUE_QUESTION_EXTRACT)
        if raw and raw.get("data"):
            q_count = len(raw["data"])
    if q_count == 0:
        dom_qs = await page.evaluate(DOM_QUESTION_EXTRACT)
        if dom_qs:
            q_count = len(dom_qs)

    return PageInfo(
        url=page.url,
        title=await page.title(),
        framework=framework,
        ui_library=ui_library,
        navigation=nav,
        has_captcha=has_captcha,
        question_count=q_count,
    )


async def extract_questions(page, framework: str) -> list[Question]:
    """从页面提取题目列表。"""
    raw = None

    if framework == "vue2":
        result = await page.evaluate(VUE_QUESTION_EXTRACT)
        if result and result.get("data"):
            raw = result["data"]

    if not raw and framework == "react":
        raw = await page.evaluate(REACT_QUESTION_EXTRACT)

    if not raw:
        raw = await page.evaluate(DOM_QUESTION_EXTRACT)

    if not raw:
        return []

    # ─── 统一规范化 ───
    questions = []
    for i, item in enumerate(raw):
        if not isinstance(item, dict):
            continue

        # 类型映射
        type_raw = str(item.get("typeId", item.get("type", item.get("questionType", "1"))))
        type_map = {
            "1": "single", "2": "multi", "3": "judge",
            "4": "fill", "5": "fill", "6": "essay",
        }
        q_type = type_map.get(type_raw, "single")

        # 题干
        title = item.get("title", item.get("questionTitle", item.get("content", item.get("stem", ""))))

        # 选项: 统一 dataArr / options / optionList
        opts_raw = item.get("dataArr") or item.get("options") or item.get("optionList") or []
        if isinstance(opts_raw, str):
            try:
                opts_raw = json.loads(opts_raw)
            except json.JSONDecodeError:
                opts_raw = []

        options = []
        for j, opt in enumerate(opts_raw):
            if isinstance(opt, dict):
                options.append(Option(
                    label=chr(65 + j),  # A, B, C, D...
                    content=opt.get("Content", opt.get("content", opt.get("label", opt.get("text", "")))),
                    is_selected=opt.get("selected", opt.get("isSelected", opt.get("checked", False))),
                ))
            elif isinstance(opt, str):
                options.append(Option(label=chr(65 + j), content=opt))

        questions.append(Question(
            id=item.get("id", item.get("questionId", f"q-{i}")),
            type=q_type,
            title=title,
            options=options,
            score=float(item.get("score", item.get("point", 0))),
            index=i + 1,
        ))

    return questions


# ─── Radio Selector Map ─────────────────────────────────────────────

RADIO_SELECTORS = {
    "iview": ".ivu-radio-input",
    "element": ".el-radio__original",
    "antd": ".ant-radio-input",
    "bootstrap": ".form-check-input",
    "native": 'input[type="radio"]',
}

CHECKBOX_SELECTORS = {
    "iview": ".ivu-checkbox-input",
    "element": ".el-checkbox__original",
    "antd": ".ant-checkbox-input",
    "bootstrap": ".form-check-input",
    "native": 'input[type="checkbox"]',
}

CARD_NUMBER_SELECTORS = [
    ".topic-zpx-main span",        # 智慧职教
    ".question-number span",       # 通用
    ".answer-card .number",        # 通用
    ".paper-num span",             # 通用
]

NEXT_BTN_SELECTORS = [
    'text=下一题',
    'button:has-text("下一题")',
    '.next-btn',
    '[class*="next"]',
]

PREV_BTN_SELECTORS = [
    'text=上一题',
    'button:has-text("上一题")',
    '.prev-btn',
    '[class*="prev"]',
]

SUBMIT_SELECTORS = [
    'text=交卷',
    'text=提交',
    'button:has-text("交卷")',
    'button:has-text("提交")',
    '.submit-btn',
    '[class*="submit"]',
]

CONFIRM_SELECTORS = [
    '.ivu-modal-wrap:not(.ivu-modal-hidden) button:has-text("确定")',
    '.ivu-modal-wrap:not(.ivu-modal-hidden) button:has-text("确认")',
    '.el-dialog:not([style*="display: none"]) button:has-text("确定")',
    '.ant-modal:not([style*="display: none"]) button:has-text("确定")',
    'button:has-text("确认提交")',
    'button:has-text("确认交卷")',
]

SUCCESS_KEYWORDS = [
    "提交成功", "已提交", "交卷成功", "试卷已提交",
    "submitted", "exam submitted", "success",
]
