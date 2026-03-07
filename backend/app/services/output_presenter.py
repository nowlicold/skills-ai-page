"""
技能执行结果经 AI 整理后再返回用户，避免直接丢原始 JSON/机械格式（类似 OpenClaw 的呈现方式）。
"""
import os
from pathlib import Path


def present_result(raw_content: str, skill_description: str, user_prompt: str) -> str:
    """
    将技能执行的原始/格式化结果交给 Claude 整理成用户友好的呈现。
    失败时返回原始内容。若内容已很短且无明显 JSON，则跳过调用以节省延迟与成本。
    """
    raw = (raw_content or "").strip()
    if len(raw) <= 400 and not raw.startswith("{") and '"status"' not in raw[:200] and '"code"' not in raw[:200]:
        return raw_content
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not key:
        env_path = Path(__file__).resolve().parent.parent.parent / ".env"
        if env_path.exists():
            for line in env_path.read_text(encoding="utf-8").splitlines():
                if line.strip().startswith("ANTHROPIC_API_KEY="):
                    key = line.split("=", 1)[1].strip().strip("'\"").strip()
                    break
    if not key:
        return raw_content

    try:
        import anthropic
        client = anthropic.Anthropic()
        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=8192,
            system="""你负责把「技能执行得到的原始结果」整理成对用户友好、易读的回复，类似 OpenClaw 的呈现方式。

通用要求：
1. 用简洁、自然的中文 + Markdown（加粗标题、列表、段落），不要编造事实，只做整理与润色。
2. 不要出现「根据以下内容」「以下是整理结果」等元描述，直接给出正文。

若内容是「视频字幕」类（含 视频标题 + 大段字幕文本）：
- 开头先给一句明确结果：**字幕抓取成功！**
- 接着写 **视频：** 视频标题（可简短概括）。
- 若字幕较长：写 **内容摘要：**，用 2～4 个要点概括视频主要内容（可带小标题如 **主要活动：**、**环境/背景：**），用列表呈现，语气自然；不必全文照贴字幕。
- 若字幕较短：可直接在 **字幕内容：** 下保留整理后的正文。
- 可适当用 emoji 增强可读性（如 ✅ 🎬 📝），不要过多。

若内容是搜索/问答类：保留「回答」「检索词」「参考来源」等结构，做少量语言优化即可。
若内容仍是 JSON 或技术输出：提取关键信息，用「回答 / 要点 / 参考」等形式重组，不要原样贴 JSON。""",
            messages=[
                {
                    "role": "user",
                    "content": f"技能简介：{skill_description or '未说明'}\n\n用户请求：{user_prompt[:500]}\n\n技能执行返回的原始内容：\n\n{raw_content[:12000]}",
                }
            ],
        )
        if not resp.content:
            return raw_content
        parts = []
        for block in resp.content:
            if getattr(block, "type", None) == "text":
                parts.append(getattr(block, "text", "") or "")
        out = "\n".join(parts).strip()
        return out if out else raw_content
    except Exception:
        return raw_content
