"""适配器注册表：上传时按顺序尝试 detect，命中则 adapt，否则交给 Claude 分析器。"""
from app.services.skill_adapters.base import CanonicalFragment, UploadHints
from app.services.skill_adapters.frontmatter import FrontmatterAdapter

# 按优先级排列；先注册的先尝试
adapters_registry: list[object] = [
    FrontmatterAdapter(),
]


def try_adapt(
    content: str,
    hints: UploadHints | None = None,
) -> CanonicalFragment | None:
    """
    遍历已注册适配器，第一个 detect 返回 True 的适配器执行 adapt，返回其结果；
    若无一命中则返回 None，由调用方走 analyze_skill。
    """
    for adapter in adapters_registry:
        if not hasattr(adapter, "detect") or not hasattr(adapter, "adapt"):
            continue
        if adapter.detect(content, hints):
            return adapter.adapt(content, hints)
    return None
