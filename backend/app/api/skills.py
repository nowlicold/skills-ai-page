import json
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from fastapi import APIRouter, File, UploadFile, HTTPException

from app.services.skill_analyzer import analyze_skill
from app.services.skill_adapters import try_adapt
from app.services.skill_adapters.base import UploadHints

router = APIRouter()

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
                    result.append(data)
                except Exception:
                    pass
    return result


@router.post("/skills/upload")
async def upload_skill(
    file: UploadFile = File(...),
    source_hint: str | None = None,
    origin_url: str | None = None,
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
    meta_file.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return meta
