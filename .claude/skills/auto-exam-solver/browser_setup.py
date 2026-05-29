"""
浏览器接入模块 — 获取已登录的 Chrome 浏览器控制权。

Usage:
    # 命令行
    python browser_setup.py start    # 关闭 Chrome 并带调试端口重启
    python browser_setup.py connect  # 验证 CDP 连接是否正常
    python browser_setup.py cookies  # 导出 Cookie 到 JSON
"""

import subprocess
import shutil
import time
import json
import os
import sys
import socket
from pathlib import Path
from urllib.request import urlopen, Request

CHROME_EXE = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
DEFAULT_PROFILE = Path(os.environ["LOCALAPPDATA"]) / r"Google\Chrome\User Data\Default"
TMP_PROFILE = Path(r"C:\Temp\chrome-debug-profile")
CDP_PORT = 9222
CDP_URL = f"http://localhost:{CDP_PORT}"


def check_port(port: int = CDP_PORT) -> bool:
    """检查 CDP 端口是否已监听。"""
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=2):
            return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False


def kill_chrome() -> bool:
    """终止所有 Chrome 进程。"""
    try:
        subprocess.run(["taskkill", "/F", "/IM", "chrome.exe"],
                       capture_output=True, timeout=10)
        time.sleep(2)
        return True
    except subprocess.TimeoutExpired:
        print("[WARN] Chrome 进程可能未完全终止")
        return False


def copy_profile(src: Path = DEFAULT_PROFILE, dst: Path = TMP_PROFILE) -> bool:
    """复制 Chrome 用户配置（含 Cookie/Storage）到临时目录。"""
    if not src.exists():
        print(f"[ERROR] 源目录不存在: {src}")
        return False

    if dst.exists():
        shutil.rmtree(dst, ignore_errors=True)
    dst.mkdir(parents=True, exist_ok=True)

    print(f"[INFO] 复制 profile: {src} -> {dst}")
    try:
        for item in src.iterdir():
            dest = dst / item.name
            try:
                if item.is_dir():
                    shutil.copytree(item, dest, symlinks=True)
                else:
                    shutil.copy2(item, dest)
            except OSError:
                pass  # 跳过被锁定的文件
        print("[OK] Profile 复制完成")
        return True
    except Exception as e:
        print(f"[ERROR] 复制失败: {e}")
        return False


def start_chrome_with_debug(
    exe: str = CHROME_EXE,
    profile: Path = TMP_PROFILE,
    port: int = CDP_PORT
) -> bool:
    """启动带远程调试端口的 Chrome。"""
    if check_port(port):
        print(f"[OK] Chrome 已在端口 {port} 运行")
        return True

    cmd = [
        exe,
        f"--remote-debugging-port={port}",
        f"--user-data-dir={profile}",
        "--restore-last-session",
    ]
    print(f"[INFO] 启动 Chrome: {' '.join(cmd)}")
    try:
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(15):  # 等待最多 15 秒
            time.sleep(1)
            if check_port(port):
                print(f"[OK] Chrome 已在端口 {port} 启动")
                return True
        print(f"[ERROR] Chrome 启动超时")
        return False
    except Exception as e:
        print(f"[ERROR] 启动失败: {e}")
        return False


def get_cdp_json(endpoint: str) -> dict | list:
    """调用 CDP HTTP API。"""
    url = f"{CDP_URL}/{endpoint}"
    try:
        req = Request(url, headers={"Host": "localhost"})
        with urlopen(req, timeout=5) as resp:
            return json.loads(resp.read())
    except Exception as e:
        print(f"[ERROR] CDP API 失败 ({url}): {e}")
        return {}


def get_connected_pages() -> list[dict]:
    """获取 CDP 浏览器中所有打开的页面。"""
    data = get_cdp_json("json")
    if isinstance(data, list):
        return [
            {"url": p.get("url", ""), "title": p.get("title", ""), "id": p.get("id", "")}
            for p in data if p.get("type") == "page"
        ]
    return []


def export_cookies_to_playwright_format() -> list[dict]:
    """
    通过 CDP 获取所有 Cookie，转换为 Playwright 可导入格式。
    需要先运行: pip install websocket-client requests
    """
    import requests

    pages = get_connected_pages()
    if not pages:
        print("[ERROR] 没有打开的页面，无法获取 Cookie")
        return []

    # 通过 CDP HTTP API 获取第一个页面的 targetId
    ws_url = None
    for entry in (get_cdp_json("json") or []):
        if entry.get("type") == "page":
            ws_url = entry.get("webSocketDebuggerUrl")
            break

    if not ws_url:
        print("[ERROR] 无法获取 WebSocket URL")
        return []

    # 使用 websocket 获取 Cookie
    try:
        from websocket import create_connection
        import json as _json

        ws = create_connection(ws_url, timeout=5)
        ws.send(_json.dumps({"id": 1, "method": "Network.getCookies"}))
        resp = _json.loads(ws.recv())
        ws.close()

        cookies = resp.get("result", {}).get("cookies", [])
        pw_cookies = []
        for c in cookies:
            pw_cookies.append({
                "name": c["name"],
                "value": c["value"],
                "domain": c.get("domain", ""),
                "path": c.get("path", "/"),
                "httpOnly": c.get("httpOnly", False),
                "secure": c.get("secure", False),
                "sameSite": c.get("sameSite", "Lax"),
            })
        print(f"[OK] 导出 {len(pw_cookies)} 个 Cookie")
        return pw_cookies
    except ImportError:
        print("[WARN] 需要 websocket-client: pip install websocket-client")
        return []


# ─── CLI ────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return

    cmd = sys.argv[1]

    if cmd == "start":
        kill_chrome()
        copy_profile()
        start_chrome_with_debug()

    elif cmd == "connect":
        if check_port():
            print(f"[OK] CDP 端口 {CDP_PORT} 可用")
            pages = get_connected_pages()
            print(f"[INFO] {len(pages)} 个页面:")
            for p in pages:
                print(f"  - {p['title'][:60] or '(无标题)'}  {p['url'][:80]}")
        else:
            print(f"[ERROR] CDP 端口 {CDP_PORT} 不可用")

    elif cmd == "cookies":
        cookies = export_cookies_to_playwright_format()
        print(json.dumps(cookies, indent=2, ensure_ascii=False))

    elif cmd == "restart":
        kill_chrome()
        start_chrome_with_debug()

    else:
        print(f"未知命令: {cmd}")
        print("可用: start | connect | cookies | restart")


if __name__ == "__main__":
    main()
