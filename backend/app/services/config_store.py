"""允许用户通过对话或 API 设置的配置项，安全写入 backend/.env（仅白名单 key）"""
from pathlib import Path

# 只允许写入这些 key，避免任意环境变量被覆盖
ALLOWED_KEYS = frozenset({"FELO_API_KEY"})

BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
ENV_PATH = BACKEND_ROOT / ".env"


def set_config(key: str, value: str) -> tuple[bool, str]:
    """
    将 key=value 写入 .env。仅允许 ALLOWED_KEYS 中的 key。
    返回 (成功, 提示信息)。
    """
    key = (key or "").strip()
    raw = (value or "").strip().replace("\n", "").replace("\r", "")
    value = raw.strip("'\"").strip()  # 去掉首尾引号，避免 Key 带引号写入导致认证失败
    if not key:
        return False, "配置项不能为空"
    if key not in ALLOWED_KEYS:
        return False, f"不允许设置 {key}，当前仅支持：{', '.join(sorted(ALLOWED_KEYS))}"
    if not value:
        return False, "配置值不能为空"

    lines: list[str] = []
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("#"):
                lines.append(line)
                continue
            if "=" in line and line.split("=", 1)[0].strip() == key:
                continue  # 丢弃旧的该 key
            lines.append(line)
    else:
        ENV_PATH.parent.mkdir(parents=True, exist_ok=True)

    # 追加新行（不写注释，避免暴露 value）
    lines.append(f'{key}={value}')
    ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")

    # 立即生效：更新当前进程环境（后续请求会重新 load_dotenv，新进程也会读新文件）
    import os
    os.environ[key] = value

    return True, "已保存，后续将使用该配置。"
