"""
Windows 专用启动脚本：先设置 ProactorEventLoop，再启动 uvicorn（单进程、无 reload）。
用 --reload 时 uvicorn 会起子进程，子进程不会先执行 main.py，策略无法生效，所以这里不用 reload。
用法：在 backend 目录下执行  python run_win.py
"""
import sys
import asyncio

if sys.platform != "win32":
    print("此脚本仅用于 Windows，其他系统请用: uvicorn app.main:app --reload")
    sys.exit(1)

asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=False,
    )
