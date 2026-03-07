"""加载 skill 的 metadata 与 SKILL.md 内容，供 chat / execute 使用"""
import json
from pathlib import Path

SKILLS_DIR = Path(__file__).resolve().parent.parent.parent / "skills"


def get_skill_dir(skill_name: str) -> Path | None:
    d = SKILLS_DIR / skill_name
    return d if d.is_dir() else None


def load_metadata(skill_name: str) -> dict | None:
    d = get_skill_dir(skill_name)
    if not d:
        return None
    meta_file = d / "metadata.json"
    if not meta_file.exists():
        return None
    try:
        return json.loads(meta_file.read_text(encoding="utf-8"))
    except Exception:
        return None


def load_skill_md(skill_name: str) -> str | None:
    d = get_skill_dir(skill_name)
    if not d:
        return None
    md = d / "SKILL.md"
    if not md.exists():
        return None
    return md.read_text(encoding="utf-8")
