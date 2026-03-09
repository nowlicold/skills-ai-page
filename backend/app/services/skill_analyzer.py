"""
上传时用 Claude 分析 SKILL.md，生成 description、ui_config、execution（HTTP 执行规格）。
这样从任意来源下载的 skill 只要上传即可被正确识别和执行，无需在后端写死。
"""
import json
import os
import re
from pathlib import Path

# 可选：从 .env 读 ANTHROPIC_API_KEY
def _get_anthropic_key() -> str:
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if key:
        return key
    env_path = Path(__file__).resolve().parent.parent.parent / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("ANTHROPIC_API_KEY="):
                return line.split("=", 1)[1].strip().strip("'\"").strip()
    return ""


def analyze_skill(skill_md: str) -> dict:
    """
    根据 SKILL.md 内容推断 description、ui_config、execution（若为 HTTP 类 skill）。
    返回可合并进 metadata 的字典；若分析失败或无法推断 execution 则 execution 为 None/缺失。
    """
    key = _get_anthropic_key()
    if not key:
        return _fallback_metadata(skill_md)

    try:
        import anthropic
        client = anthropic.Anthropic()
        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            system="""你是一个 Skill 元数据分析器。请**理解** SKILL.md 描述的执行方式（调用了哪些 API、步骤顺序、轮询逻辑等），然后输出一个 JSON 对象。只输出该 JSON，不要其他文字或 markdown 代码块。

JSON 结构要求：
- description: 一句话描述该 skill 的功能（中文），用于界面展示。
- parameters: 可选，数组，用于动态生成填写表单。每项：{ "name": "参数名", "type": "string|number|url|youtube_video_id", "label": "显示标签", "required": true/false, "description": "说明" }。name 需与 execution 中的 param_extractors 或 body/query_params 占位符一致（如 video_code、query、prompt）。若 skill 主要靠用户输入一句话则可有 name 为 "prompt" 或 "query" 的一项。
- ui_config: { "type": "chat", "supports_progress": false, "output_types": ["text", "markdown"] }；若 skill 会返回 URL 或需要进度条，可设 output_types 含 "url"、supports_progress 为 true。
- required_env: 可选，字符串数组，列出该 skill 执行时依赖的环境变量名（如 ["FELO_API_KEY"]）。仅当 execution 中出现 {{ENV:VAR_NAME}} 时输出，用于部署方知晓需配置哪些环境变量。
- execution: **仅当你能从文档中明确推断出「可执行的 HTTP/API 流程」时输出**；否则不输出 execution。
  **两种执行类型二选一：**

  (1) **单次请求**：文档描述为「一次 GET/POST 即返回结果」时，用 type "http"：
  { "type": "http", "method": "GET 或 POST", "url": "完整 URL，认证写 {{ENV:FELO_API_KEY}}", "headers": { "Authorization": "Bearer {{ENV:FELO_API_KEY}}" }, "body": 仅 POST 时如 { "query": "{{prompt}}" }, "query_params": 仅 GET 时, "param_extractors": 仅当需从用户输入提取参数如 { "video_code": "youtube_video_id" }（只允许：youtube_video_id）, "response": { "success_codes": [0, "ok", 200], "format": "answer_sources | youtube_subtitles | text" } }

  (2) **多步/异步流程**：文档描述为「先创建任务再轮询状态直到完成」（例如 PPT：POST 创建 → 用 task_id 轮询 GET 直到 COMPLETED/FAILED）时，用 type "plan"，由 steps 描述步骤，**不要**写死为某种业务名，而是按文档理解写出通用步骤：
  {
    "type": "plan",
    "timeout": 60,
    "steps": [
      { "action": "http", "method": "POST", "url": "创建任务的完整 URL", "headers": { "Authorization": "Bearer {{ENV:FELO_API_KEY}}" }, "body": { "query": "{{prompt}}" }, "extract": { "task_id": "data.task_id" } },
      { "action": "poll", "url": "轮询 URL，其中任务 ID 用 {{task_id}}，例如 https://openapi.felo.ai/v2/tasks/{{task_id}}/historical", "headers": { "Authorization": "Bearer {{ENV:FELO_API_KEY}}" }, "status_path": "data.task_status", "success_values": ["COMPLETED", "SUCCESS"], "failure_values": ["FAILED", "ERROR", "EXPIRED", "CANCELED", "PENDING"], "result": { "ppt_url": "data.ppt_url", "live_doc_url": "data.live_doc_url" }, "error_path": "data.error_message", "poll_interval": 5, "max_wait": 600 }
    ],
    "response": { "success_template": "## 任务已完成\\n\\n**链接：** [打开]({{ppt_url}})\\n\\n**在线编辑：** [LiveDoc]({{live_doc_url}})" }
  }
  规则：根据 SKILL 文档中写明的 API 端点、请求体、响应字段来填 url/body/status_path/result/error_path 等，不要臆造。认证一律用 {{ENV:FELO_API_KEY}}。

- 若 SKILL 文档中有 YAML frontmatter（--- 包裹），description 优先用 frontmatter 的 description 字段。""",
            messages=[{"role": "user", "content": skill_md[:14000]}],
        )
        text = ""
        for block in (resp.content or []):
            if getattr(block, "type", None) == "text":
                text += getattr(block, "text", "") or ""
        text = text.strip()
        # 允许被 markdown 代码块包裹
        m = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
        if m:
            text = m.group(1).strip()
        out = json.loads(text)
        if isinstance(out, dict):
            return out
    except Exception:
        pass
    return _fallback_metadata(skill_md)


def _fallback_metadata(skill_md: str) -> dict:
    """无法调用 Claude 或解析失败时，从 SKILL 里尽量提取 description，不生成 execution。"""
    desc = "上传的 Skill"
    if skill_md.strip().startswith("---"):
        fm = re.search(r"---\s*\n([\s\S]*?)\n---", skill_md)
        if fm:
            block = fm.group(1)
            for line in block.splitlines():
                if line.strip().lower().startswith("description:"):
                    desc = line.split(":", 1)[1].strip().strip("'\"").strip()
                    break
    return {
        "description": desc[:200],
        "ui_config": {"type": "chat", "supports_progress": False, "output_types": ["text", "markdown"]},
        "parameters": [],
    }
