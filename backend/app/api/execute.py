import asyncio
import json
import logging
import os
import tempfile
import shutil
import traceback
from pathlib import Path

from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

# Windows：SDK 调用 anyio.open_process(..., user=...) 会触发 NotImplementedError，在「真正发起调用」前剥掉
def _ensure_sdk_windows_open_process_patch() -> None:
    if os.name != "nt":
        return
    try:
        from claude_agent_sdk._internal.transport import subprocess_cli
        if getattr(subprocess_cli.SubprocessCLITransport, "_windows_user_patched", False):
            return
        _orig_connect = subprocess_cli.SubprocessCLITransport.connect

        async def _connect_no_user(self: object) -> None:
            import anyio
            _orig = anyio.open_process

            async def _no_user(*a: object, **kw: object) -> object:
                for k in ("user", "group", "extra_groups", "umask"):
                    kw.pop(k, None)
                return await _orig(*a, **kw)

            anyio.open_process = _no_user
            try:
                await _orig_connect(self)
            finally:
                anyio.open_process = _orig

        subprocess_cli.SubprocessCLITransport.connect = _connect_no_user
        subprocess_cli.SubprocessCLITransport._windows_user_patched = True  # type: ignore[attr-defined]
        logging.getLogger(__name__).info("已对 Claude SDK SubprocessCLITransport.connect 应用 Windows user= 补丁")
    except Exception as e:
        logging.getLogger(__name__).warning("SDK Windows 补丁未应用: %s", e)

from app.services.skill_loader import get_skill_dir, load_skill_md, load_metadata
from app.services.execution_spec import (
    run_http as run_http_by_spec,
    run_plan as run_plan_by_spec,
    run_ppt_task as run_ppt_task_by_spec,
)
from app.services.output_presenter import present_result

router = APIRouter()

CLI_INSTALL_HINT = (
    "执行需要 Claude Code CLI，当前环境无法启动。\n\n"
    "若已安装仍报错，多半是「后端进程」和「你装 claude 的终端」不是同一套 PATH：\n"
    "1. 用「能执行 claude 的那个终端」启动后端（如在该终端里运行 uvicorn），或\n"
    "2. 在启动后端前设置环境变量指向 claude：\n"
    "   Windows: set CLAUDE_CLI_PATH=%APPDATA%\\npm\\claude.cmd\n"
    "   (若 claude 不在该路径，在终端执行 where claude 查看实际路径后填进去)\n\n"
    "未安装时：请先安装 Node.js，再运行 npm install -g @anthropic-ai/claude-code，确保终端里可执行 claude。"
)


def _prepare_workspace(skill_name: str) -> str:
    """在临时目录创建 .claude/skills/{skill_name}/ 并放入 SKILL.md，返回临时目录路径"""
    skill_dir = get_skill_dir(skill_name)
    if not skill_dir:
        raise FileNotFoundError(f"Skill 不存在: {skill_name}")
    skill_md = (skill_dir / "SKILL.md").read_text(encoding="utf-8")

    tmp = tempfile.mkdtemp(prefix="skill_run_")
    root = Path(tmp)
    claude_skills = root / ".claude" / "skills" / skill_name
    claude_skills.mkdir(parents=True)
    (claude_skills / "SKILL.md").write_text(skill_md, encoding="utf-8")
    return tmp


def _is_script_not_executable(path: str) -> bool:
    """Windows 下 .cmd/.ps1 不能作为子进程 executable 直接启动（SDK 用 shell=False），必须用 .exe。"""
    if os.name != "nt":
        return False
    p = (path or "").rstrip("\\/").upper()
    return p.endswith(".CMD") or p.endswith(".PS1")


def _get_sdk_bundled_claude_exe() -> str | None:
    """返回 SDK 自带的 claude.exe 绝对路径（仅 Windows），供子进程直接执行。"""
    if os.name != "nt":
        return None
    try:
        import claude_agent_sdk
        exe = Path(claude_agent_sdk.__file__).resolve().parent / "_bundled" / "claude.exe"
        if exe.is_file():
            return str(exe)
    except Exception:
        pass
    return None


def _resolve_claude_cli_path() -> str | None:
    """解析 claude 可执行文件路径，供 SDK 使用。Windows 下仅 .cmd 时主动用 SDK 自带 claude.exe。"""
    # 1) 显式配置优先（.cmd/.ps1 不能作为 executable，跳过）
    explicit = os.environ.get("CLAUDE_CLI_PATH", "").strip()
    if explicit and Path(explicit).exists() and not _is_script_not_executable(explicit):
        logging.debug("Claude CLI 使用显式路径: %s", explicit)
        return explicit
    # 2) 当前进程 PATH 中的 claude（.cmd/.ps1 不传）
    try:
        import shutil
        which = shutil.which("claude")
        if which and Path(which).exists() and not _is_script_not_executable(which):
            logging.debug("Claude CLI 来自 PATH: %s", which)
            return which
    except Exception:
        pass
    # 3) Windows：仅 .exe 可作为子进程启动，npm 装的是 .cmd/.ps1，故直接用 SDK 自带 claude.exe
    if os.name == "nt":
        bundled = _get_sdk_bundled_claude_exe()
        if bundled:
            logging.debug("Claude CLI 使用 SDK 自带: %s", bundled)
            return bundled
    return None


async def _run_agent_sdk(
    prompt: str, cwd: str, stderr_lines: list[str] | None = None
) -> str:
    """在指定 cwd 下用 Claude Agent SDK 执行 prompt，返回收集到的文本结果。可选收集 CLI stderr 便于排查。"""
    _ensure_sdk_windows_open_process_patch()
    from claude_agent_sdk import query, ClaudeAgentOptions

    cli_path = _resolve_claude_cli_path()
    cwd_abs = str(Path(cwd).resolve())
    opts_kw: dict = {
        "cwd": cwd_abs,
        "setting_sources": ["project"],
        "allowed_tools": ["Skill", "Read", "Write", "Bash", "WebSearch", "WebFetch", "Glob", "Grep"],
    }
    if cli_path:
        opts_kw["cli_path"] = cli_path
    if stderr_lines is not None:
        opts_kw["stderr"] = lambda s: stderr_lines.append(s)
    # 显式传入 env：API Key + Windows 下补全 PATH（bundled exe 可能依赖 node）
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    env_extra: dict[str, str] = {}
    if api_key:
        env_extra["ANTHROPIC_API_KEY"] = api_key
    if os.name == "nt":
        path_add: list[str] = []
        for d in (
            os.environ.get("APPDATA", ""),
            str(Path.home() / "AppData" / "Roaming"),
            str(Path.home() / "AppData" / "Local" / "Programs"),
        ):
            if d:
                path_add.append(str(Path(d) / "npm"))
        node_glob = Path(os.environ.get("ProgramFiles", "C:\\Program Files")) / "nodejs"
        if node_glob.exists():
            path_add.append(str(node_glob))
        if path_add:
            existing = os.environ.get("PATH", "")
            env_extra["PATH"] = existing + ";" + ";".join(p for p in path_add if p)
    if env_extra:
        opts_kw["env"] = env_extra
    options = ClaudeAgentOptions(**opts_kw)
    chunks = []
    async for message in query(prompt=prompt, options=options):
        if hasattr(message, "result") and message.result is not None:
            chunks.append(str(message.result))
        if getattr(message, "subtype", None) == "text" and hasattr(message, "text"):
            chunks.append(message.text)
    return "\n\n".join(chunks).strip() if chunks else "（执行完成，无文本输出）"


def _run_via_messages_api(skill_name: str, prompt: str) -> str:
    """无 CLI 时的回退：仅用 Messages API 按 skill 说明生成回复（无真实工具调用）。"""
    import anthropic

    skill_dir = get_skill_dir(skill_name)
    if not skill_dir:
        raise FileNotFoundError(f"Skill 不存在: {skill_name}")
    skill_md = (skill_dir / "SKILL.md").read_text(encoding="utf-8")[:8000].strip()

    client = anthropic.Anthropic()
    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        system=f"""你正在按以下 Skill 说明响应用户请求。

当前环境暂时无法直接执行该 Skill（例如需要调用外部 API、运行脚本等），只能根据说明给出操作步骤和参考内容。

请用友好、易懂的话回复用户：
1. 先简短回应他的需求；
2. 明确说明「当前无法在本页面直接执行该操作」；
3. 给出具体步骤或命令（若 Skill 中有），方便用户自行在本地或其它环境执行；
4. 不要使用「简化模式」「未连接真实工具」等技术用语，改用「暂时无法在这里直接执行」「您可以按下面步骤在本地操作」等说法。

Skill 说明（SKILL.md）：\n```\n{skill_md}\n```""",
        messages=[{"role": "user", "content": prompt}],
    )
    if not resp.content:
        return "（无回复）"
    parts = []
    for block in resp.content:
        if getattr(block, "type", None) == "text":
            parts.append(getattr(block, "text", "") or "")
    return "\n".join(parts).strip() or "（无回复）"


class ExecuteRequest(BaseModel):
    skill_name: str
    parameters: dict
    # 可选：execution_mode = "sdk_only" 时仅走 Claude Agent SDK，无 CLI 直接报错不回退（与直接跑 claude CLI 一致）
    execution_mode: str | None = None


class ExecuteResult(BaseModel):
    status: str
    content: str | None = None
    url: str | None = None
    progress: int | None = None
    error: str | None = None
    result_format: str | None = None
    result_data: dict | None = None


# backend 目录下的 .env 路径（与 config_store 一致），避免从项目根启动时读不到
_BACKEND_ENV_PATH = Path(__file__).resolve().parent.parent.parent / ".env"


def _validate_execute_params(params: dict) -> str:
    """校验执行参数，返回用于执行的 prompt（可为合成字符串）；校验失败时抛出 HTTPException。"""
    if not params:
        raise HTTPException(status_code=400, detail="缺少 parameters")
    prompt = (params.get("prompt") or params.get("query") or "").strip()
    if prompt:
        return prompt
    # 无 prompt/query 时允许仅通过表单参数执行（如 video_code），用各参数值合成 prompt
    rest = [str(v).strip() for v in params.values() if v is not None and str(v).strip()]
    if not rest:
        raise HTTPException(
            status_code=400,
            detail="缺少执行参数：请提供 prompt、query 或其它必填参数",
        )
    return " ".join(rest)


def _run_execution_spec(
    execution: dict, prompt: str, meta: dict, explicit_params: dict | None = None
) -> ExecuteResult | None:
    """若 execution 可识别则执行并返回 ExecuteResult，否则返回 None。"""
    exec_type = (execution.get("type") or "").lower()
    result_format: str | None = None
    result_data: dict | None = None
    if exec_type == "http":
        ok, content, result_format, result_data = run_http_by_spec(
            execution, prompt, explicit_params
        )
    elif exec_type == "plan":
        ok, content = run_plan_by_spec(execution, prompt)
    elif exec_type == "ppt_task":
        ok, content = run_ppt_task_by_spec(execution, prompt)
    else:
        return None
    if ok:
        try:
            content = present_result(content, (meta or {}).get("description", ""), prompt)
        except Exception as e:
            logging.exception("present_result 失败，已回退为原始内容: %s", e)
        return ExecuteResult(
            status="success",
            content=content,
            result_format=result_format,
            result_data=result_data,
        )
    return ExecuteResult(status="error", error=content)


def _is_sdk_only_mode(req: ExecuteRequest) -> bool:
    """是否仅 SDK 模式：只走 Claude Agent SDK，无 CLI 时直接报错不回退（行为等同直接跑 claude CLI）。"""
    mode = (req.execution_mode or "").strip().lower() or (os.environ.get("EXECUTION_MODE") or "").strip().lower()
    return mode == "sdk_only"


@router.post("/execute", response_model=ExecuteResult)
async def execute(req: ExecuteRequest):
    """执行 Skill：主路径为 Claude Agent SDK（与 OpenClaw 同款）。无 CLI 时：仅 SDK 模式直接报错；否则回退到 execution 或 Messages API。"""
    if _BACKEND_ENV_PATH.exists():
        load_dotenv(_BACKEND_ENV_PATH, override=True)

    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise HTTPException(status_code=503, detail="未配置 ANTHROPIC_API_KEY")

    try:
        prompt = _validate_execute_params(req.parameters or {})
    except HTTPException:
        raise

    meta = load_metadata(req.skill_name)
    tmp_dir = None
    sdk_only = _is_sdk_only_mode(req)

    stderr_lines: list[str] = []
    try:
        # 1) 主路径：Claude Agent SDK（与直接跑 claude CLI 一致）；收集 CLI stderr 便于排查
        tmp_dir = _prepare_workspace(req.skill_name)
        result_text = await _run_agent_sdk(prompt, tmp_dir, stderr_lines)
        try:
            result_text = present_result(result_text, (meta or {}).get("description", ""), prompt)
        except Exception as e:
            logging.exception("present_result 失败，已回退为原始内容: %s", e)
        return ExecuteResult(status="success", content=result_text)
    except FileNotFoundError as e:
        return ExecuteResult(status="error", error=str(e))
    except Exception as e:
        from claude_agent_sdk import CLIConnectionError, CLINotFoundError

        err_msg = str(e)
        cause = getattr(e, "__cause__", None)
        if cause is not None:
            err_msg += f"\n原因: {type(cause).__name__}: {cause}"
        tb = traceback.format_exc()
        if "NotImplementedError" in tb and os.name == "nt":
            err_msg += "\n\n【Windows 必读】请用「单进程」启动后端，不要用 uvicorn --reload：在 backend 目录执行  python run_win.py"
            err_msg += f"\n\n--- 堆栈 ---\n{tb}"
        elif "NotImplementedError" in tb:
            err_msg += f"\n\n--- 堆栈 ---\n{tb}"
        if stderr_lines:
            err_msg += "\n\n--- CLI stderr ---\n" + "\n".join(stderr_lines).strip()
        # 非「未找到/未连接」类错误（含 ProcessError 等）直接返回，并带上 CLI stderr 便于排查
        if not isinstance(e, (CLINotFoundError, CLIConnectionError)):
            return ExecuteResult(status="error", error=err_msg)
        # 仅 SDK 模式：无 CLI 即报错，不尝试任何回退（体验与本地 cli 一致）
        if sdk_only:
            # 先展示 SDK 原始错误（如 "Working directory does not exist" / "Failed to start"），再给通用提示
            hint = err_msg
            if not hint.strip().startswith("执行需要"):
                hint = f"{hint}\n\n---\n\n{CLI_INSTALL_HINT.strip()}"
            resolved = _resolve_claude_cli_path()
            if not resolved:
                hint += (
                    "\n\n当前后端进程无法自动找到 claude。"
                    "请在「能执行 claude 的终端」里运行 where claude，"
                    "把输出的路径设成环境变量 CLAUDE_CLI_PATH 后重启后端。"
                )
            if stderr_lines:
                hint += "\n\n--- CLI stderr ---\n" + "\n".join(stderr_lines).strip()
            return ExecuteResult(status="error", error=hint)
        # 2) 无 CLI 且非仅 SDK：有 execution 则服务端执行，否则 Messages API
        execution = (meta or {}).get("execution")
        if isinstance(execution, dict):
            spec_result = _run_execution_spec(
                execution, prompt, meta, explicit_params=req.parameters
            )
            if spec_result is not None:
                return spec_result
        try:
            fallback_text = _run_via_messages_api(req.skill_name, prompt)
            return ExecuteResult(
                status="success",
                content=fallback_text or "（执行完成，无输出）",
            )
        except Exception as fallback_err:
            return ExecuteResult(
                status="error",
                error=CLI_INSTALL_HINT + f" 回退执行也失败: {fallback_err}",
            )
    finally:
        if tmp_dir and Path(tmp_dir).exists():
            shutil.rmtree(tmp_dir, ignore_errors=True)
