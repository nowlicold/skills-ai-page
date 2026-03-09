"""
多平台 Skill 适配器：从不同来源的 SKILL.md 识别并转换为平台统一 metadata 格式。
上传时按注册顺序执行 detect，命中则 adapt，结果与 Claude 分析器合并后写入 metadata。
"""
from app.services.skill_adapters.base import CanonicalFragment, SkillAdapter
from app.services.skill_adapters.registry import adapters_registry, try_adapt

__all__ = [
    "CanonicalFragment",
    "SkillAdapter",
    "adapters_registry",
    "try_adapt",
]
