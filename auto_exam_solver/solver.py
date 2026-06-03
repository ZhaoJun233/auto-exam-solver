"""
通用考试自动作答引擎。

Usage:
    # 方式 1: 通过命令行工具（pip install 后）
    auto-exam-solver --cdp http://localhost:9222 --interactive

    # 方式 2: 作为 Python 模块
    python -m auto_exam_solver solver --cdp http://localhost:9222 --interactive

    # 方式 3: CDP 连接已有 Chrome
    python -m auto_exam_solver.solver --cdp http://localhost:9222 --url "https://xxx.com/exam/123"

    # 方式 4: 新建 Playwright 浏览器（需 Cookie JSON）
    python -m auto_exam_solver.solver --cookies cookies.json --url "https://xxx.com/exam/123"
"""

import asyncio
import argparse
import json
from dataclasses import asdict

from playwright.async_api import async_playwright, Page

from .page_prober import (
    probe_page, extract_questions, Question, PageInfo,
    RADIO_SELECTORS, CHECKBOX_SELECTORS,
    CARD_NUMBER_SELECTORS, NEXT_BTN_SELECTORS,
    PREV_BTN_SELECTORS, SUBMIT_SELECTORS,
    CONFIRM_SELECTORS, SUCCESS_KEYWORDS,
)


# ─── Navigation Helpers ─────────────────────────────────────────────

async def navigate_to_question(page: Page, index: int, info: PageInfo) -> bool:
    """将页面导航到指定题号的题目。"""
    for _ in range(20):  # 最多尝试 20 次点击
        current = await _get_current_question_index(page, info)
        if current == index:
            return True

        if info.navigation == "card":
            # 答题卡模式：点击题号
            for selector in CARD_NUMBER_SELECTORS:
                try:
                    spans = page.locator(selector)
                    count = await spans.count()
                    for i in range(count):
                        text = (await spans.nth(i).text_content() or "").strip()
                        if text == str(index):
                            await spans.nth(i).click()
                            await asyncio.sleep(1.5)
                            return True
                except Exception:
                    continue

        elif info.navigation == "pager":
            # 翻页模式：计算方向
            if current < index:
                for selector in NEXT_BTN_SELECTORS:
                    try:
                        await page.click(selector, timeout=2000)
                        await asyncio.sleep(1.5)
                        break
                    except Exception:
                        continue
            else:
                for selector in PREV_BTN_SELECTORS:
                    try:
                        await page.click(selector, timeout=2000)
                        await asyncio.sleep(1.5)
                        break
                    except Exception:
                        continue
        else:
            # 滚动模式：所有题在同一页，不需要导航
            return True

        await asyncio.sleep(0.5)

    return False


async def _get_current_question_index(page: Page, info: PageInfo) -> int:
    """获取当前显示的题号。"""
    try:
        text = await page.evaluate("() => document.body?.innerText || ''")
        import re
        m = re.search(r'(\d+)、\[', text)
        if m:
            return int(m.group(1))
    except Exception:
        pass
    return -1


# ─── Answer Selection ───────────────────────────────────────────────

async def select_option(page: Page, question: Question, info: PageInfo) -> bool:
    """选择指定选项。"""
    ui = info.ui_library
    selector = (
        CHECKBOX_SELECTORS.get(ui, RADIO_SELECTORS["native"])
        if question.type == "multi"
        else RADIO_SELECTORS.get(ui, RADIO_SELECTORS["native"])
    )

    # 尝试选中目标选项
    for opt in question.options:
        if not opt.is_correct:
            continue
        idx = ord(opt.label) - 65  # A=0, B=1, ...
        try:
            inputs = page.locator(selector)
            count = await inputs.count()
            if idx < count:
                await inputs.nth(idx).click()
                await asyncio.sleep(1)
                return True

            # 备选：点击 label wrapper（各组件库适配）
            wrapper_map = {
                "iview": ".ivu-radio-wrapper",
                "element": ".el-radio",
                "antd": ".ant-radio-wrapper",
                "bootstrap": ".form-check",
                "native": "label",
            }
            wrapper_sel = wrapper_map.get(ui, "label")
            wrappers = page.locator(wrapper_sel)
            w_count = await wrappers.count()
            if idx < w_count:
                await wrappers.nth(idx).click()
                await asyncio.sleep(1)
                return True
        except Exception as e:
            print(f"  [WARN] 选项 {opt.label} 点击失败: {e}")
    return False
# ─── Captcha Detection ──────────────────────────────────────────────

CAPTCHA_CSS_SELECTORS = [
    '#tCaptchaDyContent',
    '#captcha',
    '.captcha-container',
    '.geetest_panel',
    '.tencent-captcha',
    '.verify-code',
    '.verification',
    '[class*="captcha"]',
    '[class*="verify"]',
    '[id*="captcha"]',
    '[id*="verify"]',
]

CAPTCHA_TEXT_KEYWORDS = [
    "安全验证", "拖动滑块", "拼图完成验证", "请完成安全验证",
    "captcha", "verify", "slider", "请点击", "请拖动",
    "识别图中", "输入验证码", "验证码", "滑块验证",
    "人机验证", "行为验证", "机器人",
]


async def check_captcha_visible(page: Page) -> bool:
    """检测页面上是否有验证码弹窗。返回 True 表示需要用户手动处理。"""
    try:
        for selector in CAPTCHA_CSS_SELECTORS:
            elem = page.locator(selector).first
            if await elem.count() > 0 and await elem.is_visible():
                return True

        for selector in [
            '.ivu-modal-wrap:not(.ivu-modal-hidden)',
            '.el-dialog:not([style*="display: none"])',
            '.ant-modal:not([style*="display: none"])',
            '.modal', '.dialog', '.overlay']:
            try:
                modal = page.locator(selector).first
                if await modal.count() > 0 and await modal.is_visible():
                    text = (await modal.text_content() or "").strip()
                    if any(kw in text for kw in CAPTCHA_TEXT_KEYWORDS):
                        return True
            except Exception:
                continue

        body_text = await page.evaluate(
            "() => document.body?.innerText?.substring(0, 2000) || ''"
        )
        critical_kw = ["拖动滑块", "拼图完成", "安全验证", "请完成安全验证"]
        if any(kw in body_text for kw in critical_kw):
            return True
    except Exception:
        pass
    return False


async def wait_for_captcha_resolution(page: Page, context: str = "") -> bool:
    """检测到验证码后暂停，等待用户手动完成。返回 True 表示继续，False 表示放弃。"""
    print(f"\n{'='*60}")
    print(f"WARNING: captcha detected! ({context})")
    print(f"{'='*60}")
    print("Please manually complete the captcha in the browser.")
    print("Press Enter to continue, or type 'q' to abort.")
    print(f"{'='*60}")

    while True:
        user_input = input(">>> ").strip().lower()
        if user_input in ['', 'y', 'yes']:
            await asyncio.sleep(1)
            still_captcha = await check_captcha_visible(page)
            if still_captcha:
                print("Captcha still appears present. Press Enter to retry, or 'f' to force.")
                force = input(">>> ").strip().lower()
                if force == 'f':
                    print("Force continuing...")
                    return True
                continue
            print("Captcha cleared, resuming...")
            return True
        elif user_input in ['q', 'quit', 'exit']:
            print("User aborted")
            return False
        else:
            print("Type 'y' to continue / 'q' to abort")


# ─── Submit ─────────────────────────────────────────────────────────

async def submit_exam(page: Page) -> bool:
    """点击交卷并确认。"""
    # 提交前检测验证码
    if await check_captcha_visible(page):
        ok = await wait_for_captcha_resolution(page, "before submit")
        if not ok:
            return False

    # 点击交卷
    for selector in SUBMIT_SELECTORS:
        try:
            await page.click(selector, timeout=3000)
            print(f"  [OK] 点击交卷: {selector}")
            break
        except Exception:
            continue
    else:
        print("  [ERROR] 未找到交卷按钮")
        return False

    await asyncio.sleep(2)


    # 检测交卷后可能出现的验证码
    if await check_captcha_visible(page):
        ok = await wait_for_captcha_resolution(page, "after submit click")
        if not ok:
            print("  [WARN] 用户放弃，提交可能未完成")
            return False
    # 确认弹窗
    for selector in CONFIRM_SELECTORS:
        try:
            btn = page.locator(selector).first
            if await btn.is_visible():
                await btn.click()
                print(f"  [OK] 确认交卷: {selector}")
                await asyncio.sleep(3)
                break
        except Exception:
            continue

    # 验证结果
    body = await page.evaluate("() => document.body?.innerText || ''")
    success = any(kw in body for kw in SUCCESS_KEYWORDS)
    if success:
        print("  [OK] 提交成功！")
    else:
        print(f"  [WARN] 未检测到提交成功标志，页面内容: {body[:200]}")
    return success


# ─── Main Solver ────────────────────────────────────────────────────

async def solve_exam(
    page: Page,
    questions: list[Question],
    info: PageInfo,
    interactive: bool = False,
) -> bool:
    """主作答流程。"""
    print(f"\n{'='*60}")
    print(f"平台信息: {info.framework} + {info.ui_library}, 导航: {info.navigation}")
    print(f"共 {len(questions)} 道题")
    print(f"{'='*60}\n")

    answered = 0

    for q in questions:
        print(f"Q{q.index}: [{q.type}] {q.title[:60]}...")

        if interactive:
            print(f"  选项: {', '.join(f'{o.label}. {o.content[:30]}' for o in q.options)}")
            user_input = input("  输入正确答案 (如 A, B, C, D, 或 s 跳过): ").strip().upper()
            if user_input in ['S', 'SKIP']:
                print("  跳过")
                continue
            # 设置答案
            for o in q.options:
                o.is_correct = (o.label == user_input)

        # 验证码检测（每题操作前）
        if await check_captcha_visible(page):
            ok = await wait_for_captcha_resolution(page, f"第{q.index}题前")
            if not ok:
                print(f"  跳过第{q.index}题")
                continue

        # 导航
        await navigate_to_question(page, q.index, info)

        # 选择
        if q.options:
            ok = await select_option(page, q, info)
            if ok:
                answered += 1
                print(f"  -> 已选择答案")
            else:
                print(f"  [WARN] 选择失败")
        else:
            print(f"  [INFO] 无选项（主观题），跳过")

        await asyncio.sleep(1)

    print(f"\n已回答 {answered}/{len(questions)} 题")

    # 提交
    if interactive:
        confirm = input("\n是否交卷? (y/n): ").strip().lower()
        if confirm != 'y':
            print("已跳过交卷")
            return False

    return await submit_exam(page)


# ─── Entry Point ────────────────────────────────────────────────────

async def main():
    parser = argparse.ArgumentParser(description="通用考试自动作答引擎")
    parser.add_argument("--cdp", default="http://localhost:9222", help="CDP 连接地址")
    parser.add_argument("--cookies", help="Cookie JSON 文件路径（新建浏览器模式）")
    parser.add_argument("--url", help="考试页面 URL")
    parser.add_argument("--interactive", action="store_true", help="交互模式：每题确认答案")
    parser.add_argument("--probe-only", action="store_true", help="仅侦查页面，不答题")
    parser.add_argument("--questions-file", help="题目 JSON 输出路径")
    args = parser.parse_args()

    async with async_playwright() as p:
        # ── 连接浏览器 ──
        if args.cookies:
            browser = await p.chromium.launch(channel="chrome", headless=False)
            context = await browser.new_context()
            with open(args.cookies, "r", encoding="utf-8") as f:
                cookies = json.load(f)
            await context.add_cookies(cookies)
            page = await context.new_page()
            if args.url:
                await page.goto(args.url, wait_until="networkidle", timeout=30000)
        else:
            browser = await p.chromium.connect_over_cdp(args.cdp)
            pages = browser.contexts[0].pages
            if args.url:
                page = await browser.contexts[0].new_page()
                await page.goto(args.url, wait_until="networkidle", timeout=30000)
            else:
                # 找现有考试页面
                page = next(
                    (p for p in pages if any(
                        kw in p.url for kw in ["exam", "paper", "homework", "test", "quiz"]
                    )),
                    pages[0],
                )

        await asyncio.sleep(3)

        # ── 侦查 ──
        info = await probe_page(page)
        print(f"\n框架: {info.framework} | UI: {info.ui_library} | 导航: {info.navigation}")
        print(f"验证码: {'有' if info.has_captcha else '无'} | 题目数: {info.question_count}")

        # ── 验证码预检（侦查后发现验证码，提示用户先处理）──
        if info.has_captcha:
            print("\n[INFO] 页面存在验证码元素，请在浏览器中先完成验证码")
            await wait_for_captcha_resolution(page, "页面侦查阶段")

        if args.probe_only:
            info_dict = asdict(info)
            print(json.dumps(info_dict, indent=2, ensure_ascii=False))
            return

        # ── 提取题目 ──
        questions = await extract_questions(page, info.framework)
        print(f"提取到 {len(questions)} 道题目")

        if args.questions_file:
            q_data = [asdict(q) for q in questions]
            with open(args.questions_file, "w", encoding="utf-8") as f:
                json.dump(q_data, f, indent=2, ensure_ascii=False)
            print(f"题目已保存到 {args.questions_file}")

        if not questions:
            print("[ERROR] 未提取到题目，请检查页面是否正确加载")
            return

        # 打印题目预览
        for q in questions:
            print(f"  Q{q.index}: [{q.type}] {q.title[:80]}")
            if q.options:
                print(f"    选项: {', '.join(f'{o.label}.{o.content[:20]}' for o in q.options[:6])}")

        if args.interactive:
            # 交互模式需要用户输入每题的正确答案
            pass  # 在 solve_exam 中处理

        # ── 作答 ──
        await solve_exam(page, questions, info, interactive=args.interactive)

        if not args.cookies:
            # 保持 CDP 连接，不关闭浏览器
            print("\n[INFO] 操作完成，浏览器保持打开")
            return
        await browser.close()


def entry_point():
    """console_scripts entry point (sync wrapper for async main)."""
    asyncio.run(main())


if __name__ == "__main__":
    asyncio.run(main())
