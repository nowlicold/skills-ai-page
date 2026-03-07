# Windows：必须最先设置 ProactorEventLoop，否则 asyncio 子进程会 NotImplementedError（放在所有其他 import 之前）
import asyncio
import sys
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from pathlib import Path as _Path
import os
from dotenv import load_dotenv

# Windows：anyio.open_process 传 user/group 会触发 NotImplementedError，必须在任何使用 anyio 的代码之前剥掉
if os.name == "nt":
    try:
        import anyio._core._subprocesses as _anyio_sub
        _open_process_orig = _anyio_sub.open_process

        async def _open_process_win(*args, user=None, group=None, extra_groups=None, umask=-1, **kwargs):
            return await _open_process_orig(
                *args, user=None, group=None, extra_groups=None, umask=-1, **kwargs
            )

        _anyio_sub.open_process = _open_process_win
        import anyio
        anyio.open_process = _open_process_win
    except Exception:
        pass

# 优先加载 backend 目录下的 .env（与 execute 一致）
_backend_env = _Path(__file__).resolve().parent.parent / ".env"
if _backend_env.exists():
    load_dotenv(_backend_env, override=True)
else:
    load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import skills, chat, execute, config as config_api

app = FastAPI(title="Skills API")


@app.on_event("startup")
def _log_claude_cli_status():
    """启动时检测 Claude CLI 是否可解析，便于排查「已安装仍报错」"""
    try:
        import logging
        import os
        log = logging.getLogger("uvicorn.error")
        path = execute._resolve_claude_cli_path()
        if path:
            if path.lower().endswith("claude.exe"):
                log.info("Claude CLI 使用 SDK 自带: %s", path)
            else:
                log.info("Claude CLI 已解析: %s", path)
        else:
            log.warning(
                "Claude CLI 未解析到路径（从「能执行 claude」的终端启动后端，或设置 CLAUDE_CLI_PATH）"
            )
    except Exception:
        pass

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(skills.router, prefix="/api", tags=["skills"])
app.include_router(chat.router, prefix="/api", tags=["chat"])
app.include_router(execute.router, prefix="/api", tags=["execute"])
app.include_router(config_api.router, prefix="/api", tags=["config"])
