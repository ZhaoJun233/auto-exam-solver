"""
Entry point for `python -m auto_exam_solver`.

Usage:
    python -m auto_exam_solver solver --cdp http://localhost:9222 --interactive
    python -m auto_exam_solver browser start
"""

import sys
import asyncio


def main():
    if len(sys.argv) < 2:
        print("Usage: python -m auto_exam_solver <command> [args...]")
        print()
        print("Commands:")
        print("  solver   Run the exam solver engine")
        print("  browser  Manage Chrome browser (start/connect/cookies/restart)")
        print()
        print("Examples:")
        print("  python -m auto_exam_solver solver --cdp http://localhost:9222 --interactive")
        print("  python -m auto_exam_solver browser start")
        print("  python -m auto_exam_solver browser connect")
        return

    cmd = sys.argv[1]
    # Remove the module entry and command from argv
    sys.argv = [sys.argv[0]] + sys.argv[2:]

    if cmd == "solver":
        from .solver import main as solver_main
        asyncio.run(solver_main())
    elif cmd == "browser":
        from .browser_setup import main as browser_main
        browser_main()
    else:
        print(f"Unknown command: {cmd}")
        print("Available: solver, browser")
        sys.exit(1)


if __name__ == "__main__":
    main()
