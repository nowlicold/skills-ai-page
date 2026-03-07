import os
import re
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import anthropic
from app.services.skill_loader import load_metadata, load_skill_md
from app.services.config_store import set_config

# 无 tools 时从回复文本中解析「可执行」标记
READY_TO_EXECUTE_PATTERN = re.compile(r"READY_TO_EXECUTE:\s*([^\n]+)")
# 无 tools 时从回复中解析「保存配置」标记（仅允许已知 key）
SAVE_CONFIG_PATTERN = re.compile(r"SAVE_CONFIG:\s*FELO_API_KEY\s*=\s*([^\n]+)")

router = APIRouter()

# 工具定义：当 Claude 认为可以执行 skill 时调用，传入用户意图的自然语言描述
EXECUTE_SKILL_TOOL = {
    "name": "execute_skill",
    "description": "当用户已明确表达要执行的操作（如搜索内容、生成 PPT 等）时调用此工具，传入一句描述用户意图的话。",
    "input_schema": {
        "type": "object",
        "properties": {
            "prompt": {
                "type": "string",
                "description": "用一句话描述用户要执行的操作，例如：搜索苏州天气、生成 React 入门教程的 5 页 PPT",
            }
        },
        "required": ["prompt"],
    },
}

# 用户可在对话中提供缺失的配置（如 Felo API Key），调用此工具后会自动保存到本地
SAVE_CONFIG_TOOL = {
    "name": "save_config",
    "description": "当用户在对话中提供或设置某项配置（例如 Felo API Key）时调用此工具，将配置保存到本地，后续请求会自动使用。仅在用户明确给出要保存的配置项名称和值时调用。",
    "input_schema": {
        "type": "object",
        "properties": {
            "key": {
                "type": "string",
                "description": "配置项名称，当前仅支持：FELO_API_KEY（Felo 搜索 API Key）",
                "enum": ["FELO_API_KEY"],
            },
            "value": {
                "type": "string",
                "description": "用户提供的配置值，例如 API Key 字符串",
            },
        },
        "required": ["key", "value"],
    },
}


def _build_system_prompt(skill_name: str, description: str, skill_md: str | None, use_tools: bool = True) -> str:
    skill_instructions = ""
    if skill_md:
        skill_instructions = skill_md[:4000].strip()
    base = f"""你正在帮助用户使用一个名为「{skill_name}」的 skill。

Skill 简介：{description}

Skill 的完整说明（SKILL.md 片段）：
```
{skill_instructions}
```

你的任务：
1. 用简短、友好的话和用户对话，引导他们说出想要做什么。
2. 不要对模糊请求（如「做个游戏」）直接执行，先追问具体需求。"""
    if use_tools:
        return base + """
3. 当用户已经明确表达了要执行的操作（例如「搜索 xxx」「生成 xxx 的 PPT」）时，请调用工具 execute_skill，在 prompt 参数里填入一句描述用户意图的话。
4. 当用户在对话中提供或设置某项配置（例如说「我的 Felo Key 是 xxx」「设置 FELO_API_KEY 为 xxx」「这是 Felo API Key: xxx」）时，请调用工具 save_config，key 填 FELO_API_KEY，value 填用户提供的完整字符串（不要省略或打码）。
5. 回复使用中文。"""
    return base + """
3. 当用户已经明确表达了要执行的操作时，在回复末尾单独一行（不要放在代码块里）写出：READY_TO_EXECUTE: <一句话描述用户意图>，例如 READY_TO_EXECUTE: 搜索 苏州天气。除此行外正常用中文回复。
4. 当用户在对话中提供 Felo API Key（例如说「我的 Felo Key 是 xxx」）时，在回复末尾单独一行写出：SAVE_CONFIG: FELO_API_KEY=用户提供的完整 key 值（不要省略），以便系统保存。
5. 回复使用中文。"""


def _messages_to_anthropic(messages: list[dict]) -> list[dict]:
    """将前端消息列表转为 Anthropic API 格式"""
    out = []
    for m in messages:
        role = m.get("role")
        content = m.get("content", "")
        if role == "user":
            out.append({"role": "user", "content": content})
        elif role == "assistant":
            out.append({"role": "assistant", "content": content})
    return out


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    skill_name: str
    messages: list[ChatMessage]


class ChatResponse(BaseModel):
    message: str
    ready_to_execute: bool = False
    parameters: dict | None = None


@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    """对话接口：使用 Claude 生成回复，并在适当时返回 ready_to_execute + parameters"""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="未配置 ANTHROPIC_API_KEY，请在环境变量或 .env 中设置",
        )

    skill_name = req.skill_name.strip()
    meta = load_metadata(skill_name)
    description = meta.get("description", "上传的 Skill") if meta else "上传的 Skill"
    skill_md = load_skill_md(skill_name)

    anthropic_messages = _messages_to_anthropic([m.model_dump() for m in req.messages])
    if not anthropic_messages or anthropic_messages[-1].get("role") != "user":
        return ChatResponse(message="请先发送一条消息。")

    client = anthropic.Anthropic()
    response = None
    used_tools = True
    system = _build_system_prompt(skill_name, description, skill_md, use_tools=True)

    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=system,
            tools=[EXECUTE_SKILL_TOOL, SAVE_CONFIG_TOOL],
            messages=anthropic_messages,
        )
    except anthropic.APIError as e:
        err_msg = (getattr(e, "message", None) or str(e)).lower()
        status = getattr(e, "status_code", None)
        if status == 403 or "forbidden" in err_msg or "request not allowed" in err_msg:
            # 当前 Key 可能不支持 tool use，改用「无工具」模式，从回复文本解析 READY_TO_EXECUTE
            used_tools = False
            system = _build_system_prompt(skill_name, description, skill_md, use_tools=False)
            try:
                response = client.messages.create(
                    model="claude-sonnet-4-6",
                    max_tokens=1024,
                    system=system,
                    messages=anthropic_messages,
                )
            except anthropic.APIError as e2:
                detail = getattr(e2, "message", str(e2))
                raise HTTPException(status_code=502, detail=f"Claude API 错误: {detail}")
        else:
            detail = getattr(e, "message", str(e))
            raise HTTPException(status_code=502, detail=f"Claude API 错误: {detail}")

    if not response.content:
        return ChatResponse(message="（无回复）")

    text_parts = []
    tool_use_block = None
    config_saved_messages: list[str] = []
    for block in response.content:
        btype = getattr(block, "type", None) or (block.get("type") if isinstance(block, dict) else None)
        if btype == "text":
            text_parts.append(getattr(block, "text", None) or (block.get("text") or ""))
        elif btype == "tool_use":
            name = getattr(block, "name", None) or (block.get("name") if isinstance(block, dict) else None)
            if name == "execute_skill":
                tool_use_block = block
            elif name == "save_config":
                inp = getattr(block, "input", None) or (block.get("input") if isinstance(block, dict) else {}) or {}
                k = inp.get("key", "") if isinstance(inp, dict) else getattr(inp, "get", lambda x: None)("key")
                v = inp.get("value", "") if isinstance(inp, dict) else getattr(inp, "get", lambda x: None)("value")
                ok, msg = set_config(str(k or "").strip(), str(v or "").strip())
                config_saved_messages.append(msg if ok else f"配置保存失败：{msg}")

    message_text = "\n".join(text_parts).strip() or "好的，正在执行…"
    if config_saved_messages:
        message_text = message_text + "\n\n" + "\n".join(config_saved_messages)

    if tool_use_block is not None:
        tool_input = getattr(tool_use_block, "input", None) or (tool_use_block.get("input") if isinstance(tool_use_block, dict) else {}) or {}
        prompt = (tool_input.get("prompt", "") if isinstance(tool_input, dict) else getattr(tool_input, "get", lambda k: None)("prompt")) or ""
        return ChatResponse(
            message=message_text,
            ready_to_execute=True,
            parameters={"prompt": prompt},
        )

    if used_tools:
        return ChatResponse(message=message_text)

    # 无 tools 模式：先解析 SAVE_CONFIG（用户提供 key 时模型会输出该行）
    save_config_match = SAVE_CONFIG_PATTERN.search(message_text)
    if save_config_match:
        value = save_config_match.group(1).strip()
        ok, msg = set_config("FELO_API_KEY", value)
        message_text = SAVE_CONFIG_PATTERN.sub("", message_text).strip()
        message_text = message_text + "\n\n" + (msg if ok else f"配置保存失败：{msg}")

    # 无 tools 模式：从回复中解析 READY_TO_EXECUTE: xxx
    match = READY_TO_EXECUTE_PATTERN.search(message_text)
    if match:
        prompt = match.group(1).strip()
        display_message = READY_TO_EXECUTE_PATTERN.sub("", message_text).strip()
        return ChatResponse(
            message=display_message or "好的，正在执行…",
            ready_to_execute=True,
            parameters={"prompt": prompt},
        )
    return ChatResponse(message=message_text)
