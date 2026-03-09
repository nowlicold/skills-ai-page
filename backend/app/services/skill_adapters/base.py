"""适配器基类与统一类型：多平台 skill 转为 canonical metadata 片段。"""
from typing import Any, Protocol


class UploadHints:
    """上传时的可选提示，用于检测来源。"""
    def __init__(
        self,
        *,
        url: str | None = None,
        source: str | None = None,
        filename: str | None = None,
    ):
        self.url = url
        self.source = source
        self.filename = filename


# 与 metadata.json 字段对齐；适配器只填能解析的，其余由 analyze_skill 补全
CanonicalFragment = dict[str, Any]  # description?, parameters?, ui_config?, execution?


class SkillAdapter(Protocol):
    """多平台 Skill 适配器协议：detect 判断是否命中，adapt 输出 canonical 片段。"""

    def detect(self, content: str, hints: UploadHints | None) -> bool:
        """判断当前内容是否来自该适配器所代表的平台/格式。"""
        ...

    def adapt(self, content: str, hints: UploadHints | None) -> CanonicalFragment:
        """从原始内容解析并输出 canonical 片段，缺失字段可省略。"""
        ...
