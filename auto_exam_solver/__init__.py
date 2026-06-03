"""
auto-exam-solver — 通用在线考试/作业自动答题助手。

支持各类教育平台（智慧职教、超星、学堂在线等），自适应 Vue/React/原生 HTML。
"""

from .page_prober import (
    probe_page,
    extract_questions,
    Question,
    Option,
    PageInfo,
    RADIO_SELECTORS,
    CHECKBOX_SELECTORS,
    CARD_NUMBER_SELECTORS,
    NEXT_BTN_SELECTORS,
    PREV_BTN_SELECTORS,
    SUBMIT_SELECTORS,
    CONFIRM_SELECTORS,
    SUCCESS_KEYWORDS,
)

from .solver import solve_exam, main as solver_main
from .browser_setup import main as browser_setup_main

__version__ = "2.1.0"
__all__ = [
    "probe_page",
    "extract_questions",
    "solve_exam",
    "Question",
    "Option",
    "PageInfo",
    "solver_main",
    "browser_setup_main",
]
