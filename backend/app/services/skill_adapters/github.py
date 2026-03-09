"""GitHub 来源的 Skill 适配器：origin_url 含 github.com 或 source_hint 为 github。"""
import re
from app.services.skill_adapters.base import CanonicalFragment, UploadHints


class GitHubAdapter:
    """
    检测：origin_url 包含 github.com，或 source_hint 为 github。
    转换：与通用 frontmatter 一致，从 YAML 块抽取 description 等。
    """

    def detect(self, content: str, hints: UploadHints | None) -> bool:
        if not hints:
            return False
        if hints.source and "github" in (hints.source or "").lower():
            return True
        if hints.url and "github.com" in (hints.url or "").lower():
            return True
        return False

    def adapt(self, content: str, hints: UploadHints | None) -> CanonicalFragment:
        out: CanonicalFragment = {}
        if not (content or "").strip().startswith("---"):
            return out
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
