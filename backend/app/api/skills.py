import json
import re
from datetime import datetime, timezone
from pathlib import Path
import urllib.request
import urllib.error
from urllib.parse import urlparse
from dotenv import load_dotenv
from fastapi import APIRouter, File, Form, UploadFile, HTTPException
from pydantic import BaseModel

from app.services.skill_analyzer import analyze_skill
from app.services.skill_adapters import try_adapt
from app.services.skill_adapters.base import UploadHints

router = APIRouter()

_ENV_PLACEHOLDER_RE = re.compile(r"\{\{ENV:([A-Za-z0-9_]+)\}\}")


def _extract_required_env(obj: dict | list | str) -> list[str]:
    """从 execution（或任意嵌套结构）中提取 {{ENV:VAR_NAME}} 出现的变量名，去重并保持顺序。"""
    seen: set[str] = set()
    result: list[str] = []

    def _walk(o):
        if isinstance(o, dict):
            for v in o.values():
                _walk(v)
        elif isinstance(o, list):
            for v in o:
                _walk(v)
        elif isinstance(o, str):
            for m in _ENV_PLACEHOLDER_RE.finditer(o):
                name = m.group(1)
                if name not in seen:
                    seen.add(name)
                    result.append(name)

    _walk(obj)
    return result

SKILLS_DIR = Path(__file__).resolve().parent.parent.parent / "skills"
SKILLS_DIR.mkdir(parents=True, exist_ok=True)
_BACKEND_ENV = Path(__file__).resolve().parent.parent.parent / ".env"


@router.get("/skills")
def list_skills():
    """列出所有 skills（从 skills/ 目录读取 metadata.json）"""
    result = []
    if not SKILLS_DIR.exists():
        return result
    for d in SKILLS_DIR.iterdir():
        if d.is_dir():
            meta = d / "metadata.json"
            if meta.exists():
                try:
                    data = json.loads(meta.read_text(encoding="utf-8"))
                    if "required_env" not in data and data.get("execution"):
                        data["required_env"] = _extract_required_env(data["execution"])
                    result.append(data)
                except Exception:
                    pass
    return result


@router.post("/skills/upload")
async def upload_skill(
    file: UploadFile = File(...),
    source_hint: str | None = Form(None),
    origin_url: str | None = Form(None),
):
    """上传 SKILL.md；多平台适配器优先识别来源并转换，再与 Claude 分析结果合并，任意来源的 skill 均可被正确执行。"""
    if not file.filename or not file.filename.endswith(".md"):
        raise HTTPException(status_code=400, detail="请上传 .md 文件")
    name = Path(file.filename).stem
    if name.lower() == "skill":
        name = "skill-uploaded"
    skill_dir = SKILLS_DIR / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    path = skill_dir / "SKILL.md"
    content = await file.read()
    text = content.decode("utf-8", errors="replace")
    path.write_bytes(content)

    if _BACKEND_ENV.exists():
        load_dotenv(_BACKEND_ENV, override=True)

    hints = UploadHints(
        url=origin_url,
        source=source_hint,
        filename=file.filename,
    )
    adapter_fragment = try_adapt(text, hints)
    analyzed = analyze_skill(text)

    # 合并：适配器提供的字段优先，其余用 Claude 分析结果
    def _pick(key: str, default=None):
        val = None
        if adapter_fragment and adapter_fragment.get(key) is not None:
            val = adapter_fragment.get(key)
        if val is None:
            val = analyzed.get(key)
        return val if val is not None else default

    meta = {
        "name": name,
        "description": _pick("description") or "上传的 Skill",
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "author": "anonymous",
        "ui_config": _pick("ui_config") or {
            "type": "chat",
            "supports_progress": False,
            "output_types": ["text", "markdown"],
        },
    }
    if _pick("parameters") is not None:
        meta["parameters"] = _pick("parameters")
    if _pick("execution"):
        meta["execution"] = _pick("execution")
    if _pick("required_env") is not None:
        meta["required_env"] = _pick("required_env")
    elif meta.get("execution"):
        meta["required_env"] = _extract_required_env(meta["execution"])
    (skill_dir / "metadata.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return meta


def _fetch_url_to_text(url: str) -> str:
    """从 URL 拉取内容为文本。GitHub blob 自动转为 raw。"""
    u = url.strip()
    if not u.startswith("http://") and not u.startswith("https://"):
        raise HTTPException(status_code=400, detail="请输入有效的 http(s) URL")
    # GitHub 网页 URL 转 raw
    if "github.com" in u and "/blob/" in u:
        u = u.replace("github.com", "raw.githubusercontent.com", 1).replace("/blob/", "/", 1)
    req = urllib.request.Request(u, headers={"User-Agent": "SkillsAI-Platform/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        raise HTTPException(status_code=400, detail=f"拉取失败（HTTP {e.code}）")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"拉取失败：{e!s}")


def _skill_name_from_url(url: str) -> str:
    """从 URL 路径推断 skill 目录名，如 .../felo-web-fetch/README.md -> felo-web-fetch。"""
    path = urlparse(url).path
    parts = [p for p in path.split("/") if p and p != "blob"]
    if len(parts) >= 2 and parts[-1].lower().endswith(".md"):
        return parts[-2]
    if parts and parts[-1].lower().endswith(".md"):
        return Path(parts[-1]).stem or "skill-imported"
    return "skill-imported"


class ImportFromUrlRequest(BaseModel):
    url: str
    source_hint: str | None = None


@router.post("/skills/import-from-url")
async def import_skill_from_url(body: ImportFromUrlRequest):
    """从链接拉取 .md 内容并导入为 skill（与上传后流程一致：适配器 + 分析 → 写入 metadata）。"""
    if _BACKEND_ENV.exists():
        load_dotenv(_BACKEND_ENV, override=True)
    text = _fetch_url_to_text(body.url.strip())
    if not text.strip():
        raise HTTPException(status_code=400, detail="该链接返回内容为空")
    name = _skill_name_from_url(body.url.strip())
    if name.lower() == "skill":
        name = "skill-imported"
    skill_dir = SKILLS_DIR / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(text, encoding="utf-8")

    hints = UploadHints(url=body.url.strip(), source=body.source_hint, filename=None)
    adapter_fragment = try_adapt(text, hints)
    analyzed = analyze_skill(text)

    def _pick(key: str, default=None):
        val = adapter_fragment.get(key) if adapter_fragment else None
        if val is None:
            val = analyzed.get(key)
        return val if val is not None else default

    meta = {
        "name": name,
        "description": _pick("description") or "从链接导入的 Skill",
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "author": "anonymous",
        "ui_config": _pick("ui_config") or {
            "type": "chat",
            "supports_progress": False,
            "output_types": ["text", "markdown"],
        },
    }
    if _pick("parameters") is not None:
        meta["parameters"] = _pick("parameters")
    if _pick("execution"):
        meta["execution"] = _pick("execution")
    if _pick("required_env") is not None:
        meta["required_env"] = _pick("required_env")
    elif meta.get("execution"):
        meta["required_env"] = _extract_required_env(meta["execution"])
    (skill_dir / "metadata.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return meta


@router.post("/skills/{skill_name}/analyze")
async def analyze_skill_by_name(skill_name: str):
    """对已上传的 Skill 重新分析 SKILL.md，更新 metadata 中的 description、ui_config、execution（不覆盖 name/created_at/author）。"""
    skill_dir = SKILLS_DIR / skill_name
    if not skill_dir.is_dir():
        raise HTTPException(status_code=404, detail="Skill 不存在")
    md_file = skill_dir / "SKILL.md"
    if not md_file.exists():
        raise HTTPException(status_code=400, detail="该 Skill 无 SKILL.md")
    meta_file = skill_dir / "metadata.json"
    existing = {}
    if meta_file.exists():
        try:
            existing = json.loads(meta_file.read_text(encoding="utf-8"))
        except Exception:
            pass
    if _BACKEND_ENV.exists():
        load_dotenv(_BACKEND_ENV, override=True)
    text = md_file.read_text(encoding="utf-8")
    analyzed = analyze_skill(text)
    meta = {
        "name": existing.get("name") or skill_name,
        "description": analyzed.get("description") or existing.get("description") or "上传的 Skill",
        "created_at": existing.get("created_at") or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "author": existing.get("author", "anonymous"),
        "ui_config": analyzed.get("ui_config") or existing.get("ui_config") or {"type": "chat", "supports_progress": False, "output_types": ["text", "markdown"]},
    }
    if analyzed.get("parameters") is not None:
        meta["parameters"] = analyzed["parameters"]
    elif "parameters" in existing:
        meta["parameters"] = existing["parameters"]
    if analyzed.get("execution"):
        meta["execution"] = analyzed["execution"]
    elif "execution" in existing:
        meta["execution"] = existing["execution"]
    if analyzed.get("required_env") is not None:
        meta["required_env"] = analyzed["required_env"]
    elif "required_env" in existing:
        meta["required_env"] = existing["required_env"]
    elif meta.get("execution"):
        meta["required_env"] = _extract_required_env(meta["execution"])
    meta_file.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return meta
