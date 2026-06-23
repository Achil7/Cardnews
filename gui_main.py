"""밈 카드뉴스 반수동 GUI — 진입점."""
import os
import sys
import threading
import webbrowser

import uvicorn

from src.db.repository import init_db

PORT = 8501


def main():
    init_db()

    # Docker/서버에서는 브라우저 안 열고, 로컬에서만 자동 오픈
    if os.environ.get("DISPLAY") or sys.platform == "win32":
        threading.Timer(1.5, lambda: webbrowser.open(f"http://localhost:{PORT}")).start()

    uvicorn.run("src.gui.app:app", host="127.0.0.1", port=PORT, log_level="info")


if __name__ == "__main__":
    main()
