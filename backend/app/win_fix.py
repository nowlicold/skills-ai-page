"""
Windows 下必须先设置 ProactorEventLoop，再让 uvicorn 创建事件循环，否则子进程会 NotImplementedError。
用法：uvicorn app.win_fix:app --reload
"""
import sys
import asyncio

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from app.main import app

__all__ = ["app"]
