"""通用 Frontmatter 适配器：识别 YAML frontmatter，抽取 description、source 等。"""
import re
from app.services.skill_adapters.base import CanonicalFragment, UploadHints


class FrontmatterAdapter:
    """
    检测：SKILL.md 以 --- 开头且含 YAML 块。
    转换：从 frontmatter 抽取 description；若有 source/platform 等可留作后续扩展。
    """

    def detect(self, content: str, hints: UploadHints | None) -> bool:
        if not (content or "").strip().startswith("---"):
            return False
        return bool(re.search(r"---\s*\n[\s\S]*?\n---", content))

    def adapt(self, content: str, hints: UploadHints | None) -> CanonicalFragment:
        out: CanonicalFragment = {}
        m = re.search(r"---\s*\n([\s\S]*?)\n---", content)
        if not m:
            return out
        block = m.group(1)
        for line in block.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if ":" not in line:
                continue
            key, _, val = line.partition(":")
            key = key.strip().lower()
            val = val.strip().strip("'\"").strip()
            if key == "description" and val:
                out["description"] = val[:500]
        return out
