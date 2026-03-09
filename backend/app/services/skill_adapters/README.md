# 多平台 Skill 适配器

用户可能从 Cursor、GitHub、Felo 等不同渠道下载 SKILL.md，格式/元数据位置不一。适配器负责**识别来源**并**转换为平台统一 metadata**，上传流程会先走适配器，再与 Claude 分析结果合并。

## 接口

- **detect(content, hints) → bool**：判断是否命中该平台/格式。
- **adapt(content, hints) → CanonicalFragment**：解析出 `description`、`parameters`、`ui_config`、`execution` 等（能解析多少填多少，其余由 `skill_analyzer` 补全）。

`UploadHints` 可选：`url`、`source`、`filename`，用于检测时参考。

## 扩展新平台

1. 在本目录新建模块，实现带 `detect` / `adapt` 的类（或实现 `SkillAdapter` 协议）。
2. 在 `registry.py` 的 `adapters_registry` 中追加该适配器实例（顺序=优先级）。
3. 无需改上传 API 或执行逻辑。

详见项目根目录 `design-mvp.md` 中「8. 多平台 Skill 接入与自动化适配」。
