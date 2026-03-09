"""Cursor 来源的 Skill 适配器：frontmatter 含 source/platform: cursor 或文件名/来源提示为 cursor。"""
import re
from app.services.skill_adapters.base import CanonicalFragment, UploadHints


class CursorAdapter:
    """
    检测：source_hint 为 cursor、文件名含 cursor，或 frontmatter 内 source/platform 为 cursor。
    转换：从 frontmatter 抽取 description；若有 triggers/params 等可映射为 parameters 雏形。
    """

    def detect(self, content: str, hints: UploadHints | None) -> bool:
        if hints:
            if hints.source and "cursor" in (hints.source or "").lower():
                return True
            if hints.filename and "cursor" in (hints.filename or "").lower():
                return True
        if not (content or "").strip().startswith("---"):
            return False
        m = re.search(r"---\s*\n([\s\S]*?)\n---", content)
        if not m:
            return False
        block = m.group(1).lower()
        if "source:" in block and "cursor" in block:
            return True
        if "platform:" in block and "cursor" in block:
            return True
        return False

    def adapt(self, content: str, hints: UploadHints | None) -> CanonicalFragment:
        out: CanonicalFragment = {}
        m = re.search(r"---\s*\n([\s\S]*?)\n---", content)
        if not m:
            return out
        block = m.group(1)
        for line in block.splitlines():
            line_stripped = line.strip()
            if not line_stripped or line_stripped.startswith("#"):
                continue
            if ":" not in line_stripped:
                continue
            key, _, val = line_stripped.partition(":")
            key = key.strip().lower()
            val = val.strip().strip("'\"").strip()
            if key == "description" and val:
                out["description"] = val[:500]
        return out
