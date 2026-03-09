# Design: Interactive Skills Platform (MVP)

> Status: Draft
> Created: 2026-03-06
> Repo: skills-ai-page (Monorepo)

## Background

Skills 创作者创作了有用的 skills（Claude Code/OpenClaw），但这些 skills 只能在命令行工具中运行，只有技术用户能用。创作者希望让更多非技术用户也能使用自己的 skills，从而扩大 skills 的影响力和价值。

## 需求理解

目标用户是**小白**：不会用 Claude Code（cc）或 OpenClaw，也不知道去哪搞 skills。产品要解决三件事：

| 谁         | 小白用户：不会用 Claude Code / OpenClaw                                                                                                                                                |
| ---------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 痛点 1     | **不知道在哪搞 skills** — 不知道要装什么、skills 放哪个目录、怎么配置                                                                                                                  |
| 痛点 2     | **没有「用」的入口** — 即使用户拿到一个 SKILL.md，也没有简单界面让他们填信息、点一下就能用                                                                                             |
| 产品要做的 | ① 给一个**上传（或获取）skills** 的地方<br>② 上传后有一个**界面**让他们**填写/输入**<br>③ 用**交互式对话**引导，而不是冷冰冰的表单<br>④ 最后**帮他们执行**这个 skill，并把结果展示出来 |

一句话：让「不会用 cc/openclaw」的人，在网页里**上传 skill → 用对话填好要什么 → 你帮他在后端执行并给结果**。

## 需求点清单

与设计/评审对齐时可直接对照：

| #   | 需求点                    | 说明                                                                                                    |
| --- | ------------------------- | ------------------------------------------------------------------------------------------------------- |
| 1   | **上传/获取 skill**       | 用户能「上传一个 SKILL.md」或从平台选一个已存在的 skill；不需要知道 `~/.claude/skills` 或任何本地路径。 |
| 2   | **有界面**                | 选好/上传好 skill 后，有一个明确的「使用这个 skill」的页面，而不是命令行。                              |
| 3   | **填写方式 = 交互式对话** | 用对话引导用户输入（例如「你想搜什么？」「想生成什么主题的 PPT？」），而不是先展示一堆参数名/表单字段。 |
| 4   | **可选：简单表单**        | 若某些 skill 参数固定、简单，可同时支持「对话收集」或「表单填写」，以对话为主、表单为辅。               |
| 5   | **代为执行**              | 参数收集完后，在后端/云端执行该 skill（不要求用户装 Claude Code/OpenClaw），执行结果在同一界面展示。    |
| 6   | **结果展示**              | 根据 skill 类型展示文本、链接、进度等（与「动态 UI」设计一致）。                                        |

## Problem Statement

**WHO**: Skills 创作者

**SITUATION**:

- 创作了有用的 skills（可能包含 Python 脚本、CLI 调用等）
- 想让更多人使用自己的 skills
- 但 skills 只能在 Claude Code/OpenClaw 中运行，只有技术用户能用

**PROBLEM**:
Skills 的传播和使用受限于技术门槛 — 潜在用户装不好 Claude Code/OpenClaw，创作者的作品无法触达非技术用户

**IMPACT**:

- 创作者的作品价值无法最大化
- 好的 skills 埋没在技术圈子里
- 无法形成 skills 创作者生态

## Related Features

目前没有 .features/ 目录，这是新项目。

## Goals

1. **降低 skills 使用门槛** - 非技术用户无需安装 Claude Code，通过 Web 界面即可使用 skills
2. **智能交互体验** - 对话式引导 + 动态 UI，不只是填表单
3. **验证核心价值** - 用真实 skills（felo-skills）验证方案可行性

## Non-Goals

- ❌ 安全沙箱隔离（MVP 阶段不考虑，后面迭代）
- ⚠️ **MVP 无沙箱，仅限受控/内测环境使用**；不可在公网对不可信用户开放未审核 skills。
- ❌ 用户认证和权限管理（MVP 阶段不考虑）
- ❌ Skills 市场功能（发布、评分、付费等）
- ❌ 复杂的数据可视化（图表、地图等，MVP 只支持基础 UI）

## Jobs to be Done

**Functional Job**:

- Skills 创作者：让我的 skills 能被更多人使用
- 普通用户：不需要懂技术就能用 skills 完成任务

**Social Job**:

- 创作者：展示自己的作品，获得认可
- 用户：使用先进的 AI 工具，提升效率

**Emotional Job**:

- 创作者：成就感（作品被使用）
- 用户：轻松感（不需要学习复杂工具）

## Solution

### Overview

**产品定位**：做一个**可视化的 OpenClaw** —— 即 Agent WebApp，底层以 **Claude Agent SDK** 为主引擎执行 skills，与 OpenClaw/Claude Code 同源；前端提供选 Skill、对话输入、查看执行结果的 Web 界面，无需用户安装 CLI。

创建一个 Web 平台，用户上传 Claude Code 标准的 SKILL.md 文件，平台使用 Claude API 分析 skill 并生成交互界面，通过**官方 Claude Agent SDK** 执行 skills。

**执行层**：

- **主路径**：采用 [Claude Agent SDK](https://platform.claude.com/docs/en/agent-sdk/overview)（Python：`pip install claude-agent-sdk`）。SDK 从**文件系统**加载 Skills（`.claude/skills/<name>/SKILL.md`），无程序式注册 API；运行时将平台存储 `skills/{name}/` 映射为临时目录内 `.claude/skills/{name}/`，再以 `query(prompt=..., options=ClaudeAgentOptions(cwd=..., allowed_tools=["Skill", "Read", "Write", "Bash", "WebSearch", ...]))` 执行，行为与 OpenClaw 一致。
- **回退**：当环境无 Claude Code CLI（无法启动 SDK）时，若 skill 的 metadata 含有 `execution`（由分析器根据 SKILL.md 理解生成），则在服务端按 http/plan 等规格直接调用 API 并返回结果；否则用 Messages API 生成操作说明，引导用户本地执行。

**执行模式**：

- **默认**：先走 SDK，无 CLI 时再按 execution / Messages API 回退，适合「服务器未装 CLI 也要能出结果」的部署。
- **仅 SDK（`execution_mode=sdk_only`）**：请求体传 `execution_mode: "sdk_only"` 或环境变量 `EXECUTION_MODE=sdk_only`。只走 Claude Agent SDK，无 CLI 时直接返回错误、不做任何回退，行为与本地直接跑 `claude` CLI 一致；适合「本机已装 CLI、希望 Web 只是壳」的场景，避免回退导致体验与 CLI 不一致。

**Windows 已知问题（后端启动）**：

- 在 Windows 上若用 `uvicorn app.main:app --reload` 启动，执行 skill 时会报 **`Failed to start Claude Code: NotImplementedError`**。
- **原因**：`--reload` 时 uvicorn 会起子进程跑服务，子进程不会先执行 `main.py` 里的事件循环设置；Windows 默认 **SelectorEventLoop** 不支持子进程（`asyncio.create_subprocess_exec` 会走 `base_events._make_subprocess_transport` 并抛出 NotImplementedError），必须使用 **ProactorEventLoop**（在创建事件循环前设置 `asyncio.WindowsProactorEventLoopPolicy()`）。
- **解决**：Windows 上**不要用** `uvicorn ... --reload`，改用单进程启动脚本：在 `backend` 目录执行 `python run_win.py`。该脚本会先设置 `WindowsProactorEventLoopPolicy()`，再以 `reload=False` 启动 uvicorn。改代码后需重启时，Ctrl+C 停掉再重新执行 `python run_win.py` 即可。

**核心特性：**

1. **对话式交互（A）** - 用户不填表单，而是跟 AI 对话，AI 引导用户提供必要信息
2. **动态 UI（B）** - 根据 skill 特性生成不同的交互界面（进度条、链接、预览等）

### Architecture

**Monorepo 结构：**

```
skills-ai-page/
├── frontend/          # React + TypeScript
│   ├── src/
│   │   ├── components/
│   │   │   ├── Chat/           # 对话界面
│   │   │   ├── SkillUpload/    # 上传 skills
│   │   │   ├── DynamicUI/      # 动态 UI 组件
│   │   │   │   ├── ProgressBar.tsx
│   │   │   │   ├── LinkOutput.tsx
│   │   │   │   └── TextOutput.tsx
│   │   │   └── SkillList/      # Skills 列表
│   │   ├── pages/
│   │   ├── hooks/
│   │   └── store/              # Zustand 状态管理
│   └── package.json
├── backend/           # Python + FastAPI
│   ├── app/
│   │   ├── api/
│   │   │   ├── skills.py       # Skills CRUD
│   │   │   ├── chat.py         # 对话接口
│   │   │   └── execute.py      # 执行 skills
│   │   ├── services/
│   │   │   ├── skill_analyzer.py    # Claude 分析 SKILL.md
│   │   │   ├── agent_executor.py    # Claude Agent SDK 执行
│   │   │   └── ui_generator.py      # 生成 UI 配置
│   │   └── storage/
│   │       └── file_storage.py      # 文件系统存储
│   ├── skills/                      # Skills 存储目录
│   │   ├── felo-search/
│   │   │   ├── SKILL.md
│   │   │   └── metadata.json
│   │   └── felo-slides/
│   │       ├── SKILL.md
│   │       └── metadata.json
│   └── requirements.txt
└── README.md
```

### Detailed Design

#### 1. Skills 上传与存储

**用户上传 SKILL.md：**

- 前端：文件上传组件
- 后端：接收文件，保存到 `skills/{skill-name}/SKILL.md`
- 生成 `metadata.json`（创建时间、skill 名称等）

**文件存储结构：**

```
skills/
├── felo-search/
│   ├── SKILL.md
│   └── metadata.json
└── felo-slides/
    ├── SKILL.md
    └── metadata.json
```

**metadata.json 格式：**

```json
{
  "name": "felo-search",
  "description": "Real-time web search",
  "created_at": "2026-03-06T10:00:00Z",
  "author": "anonymous",
  "ui_config": {
    "type": "chat",
    "supports_progress": false,
    "output_types": ["text", "markdown"]
  }
}
```

#### 2. AI 分析 SKILL.md

**调用 Claude API 分析：**

- 输入：SKILL.md 内容
- 输出：
  - Skill 功能描述
  - 需要的参数（名称、类型、描述）
  - 需要的 UI 类型（chat、progress、link 等）
  - 预期输出类型（text、file、url 等）

**Prompt 示例：**

```
分析以下 SKILL.md，提取：
1. Skill 的功能描述（一句话）
2. 需要的输入参数（JSON 格式）
3. 需要的 UI 类型（chat/progress/link）
4. 预期输出类型（text/file/url）

SKILL.md:
{skill_content}

返回 JSON 格式。
```

**返回示例：**

```json
{
  "description": "Real-time web search with AI-generated answers",
  "parameters": [
    {
      "name": "query",
      "type": "string",
      "description": "Search query",
      "required": true
    }
  ],
  "ui_type": "chat",
  "supports_progress": false,
  "output_types": ["text", "markdown"]
}
```

#### 3. 对话式交互

**用户点击"使用这个 skill"：**

1. 进入对话界面（类似 ChatGPT）
2. AI 发送欢迎消息：「这个 skill 可以帮你 {description}，你想做什么？」
3. 用户输入需求
4. AI 引导用户提供必要参数（对话式）
5. 参数收集完成后，调用后端执行 skill

**对话 → 执行协议（Blocker）**  
需在实现前约定，避免前后端歧义：

- **谁判定参数收齐**：由后端对话接口在每轮 Claude 回复中判断（或由 Claude 在回复中附带结构化标记）。
- **返回结构**：对话接口除返回「给用户看的消息」外，可附带 `ready_to_execute: boolean` 与 `parameters: Record<string, unknown>`；当 `ready_to_execute === true` 时，前端发起执行请求。
- **前端何时调执行**：前端在收到 `ready_to_execute: true` 且携带 `parameters` 的响应后，调用 `POST /execute`（或等价接口），传入 `skill_name` + `parameters`。  
  若采用流式对话，需约定是同一响应内携带上述字段，还是单独一条「系统消息」用于触发执行。

**对话流程示例（felo-search）：**

```
AI: 这个 skill 可以帮你进行实时网络搜索，你想搜索什么？
User: 东京今天天气
AI: 好的，正在搜索"东京今天天气"...
[调用 skill 执行]
AI: [展示搜索结果]
```

**对话流程示例（felo-slides）：**

```
AI: 这个 skill 可以帮你生成 PPT，你想生成什么主题的 PPT？
User: React 入门教程，5 页
AI: 好的，正在生成"React 入门教程"PPT，大约需要 5-10 分钟...
[显示进度条]
AI: PPT 生成完成！[点击查看](https://...)
```

#### 4. 动态 UI 渲染

**根据 skill 的 ui_config 渲染不同的 UI：**

**A) 基础对话（默认）：**

- 文本输入/输出
- Markdown 渲染

**B) 进度展示：**

- 进度条组件
- 状态文本（进行中/完成/失败）
- 用于长时间运行的 skills（如 felo-slides）

**C) 链接输出：**

- 可点击的链接
- 可选：iframe 预览

**前端组件：**

```tsx
// DynamicUI.tsx
function DynamicUI({ uiConfig, data }) {
  if (uiConfig.supports_progress && data.status === "running") {
    return <ProgressBar progress={data.progress} />;
  }

  if (uiConfig.output_types.includes("url")) {
    return <LinkOutput url={data.url} />;
  }

  return <TextOutput content={data.content} />;
}
```

#### 5. 执行 Skills

**执行前参数校验（Blocker）**  
后端在执行前必须对 `parameters` 做校验：类型、必填项、长度/范围等，与 skill 分析得到的参数 schema 一致；校验失败返回 400 及明确错误信息。禁止将用户输入未经校验直接传入 shell/脚本，防止注入。

**后端使用 Claude Agent SDK 执行：**

SDK 要求 Skills 位于文件系统的 `.claude/skills/<name>/SKILL.md`，且通过 `setting_sources=["project"]`、`cwd` 指向含该目录的路径来加载。平台当前存于 `skills/{skill_name}/SKILL.md`，执行时需做**目录映射**（例如为本次执行创建临时目录，在其中建 `.claude/skills/{skill_name}/` 并放入或链接当前 skill），再调用 `query(prompt=..., options=...)`。

```python
# agent_executor.py（概念示例，以官方 API 为准）
import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions

async def execute_skill(skill_name: str, parameters: dict):
    # 将 parameters 转为自然语言/结构化 prompt，例如：
    # "用户要搜索：东京今天天气" 或 "用户要生成 PPT：React 入门教程，5 页"
    user_prompt = build_prompt_from_parameters(skill_name, parameters)

    # 执行目录：需包含 .claude/skills/{skill_name}/SKILL.md（从 skills/ 映射或复制）
    run_cwd = prepare_skill_workspace(skill_name)  # 返回含 .claude/skills/ 的目录

    options = ClaudeAgentOptions(
        cwd=run_cwd,
        setting_sources=["project"],
        allowed_tools=["Skill", "Read", "Write", "Bash", "WebSearch", "WebFetch"],  # 按 skill 需要配置
    )

    result_messages = []
    async for message in query(prompt=user_prompt, options=options):
        result_messages.append(message)
    return collect_result(result_messages)  # 从 message 流中提取最终结果给前端
```

- 官方文档：[Agent SDK Overview](https://platform.claude.com/docs/en/agent-sdk/overview)、[Agent SDK - Skills](https://platform.claude.com/docs/en/agent-sdk/skills)
- SDK 无 `execute(parameters)` 式 API，用户意图与参数通过 **prompt** 传入；对话阶段收集到的 `parameters` 在调用执行前需转成上述 `user_prompt`。

**执行流程：**

1. 前端发送执行请求（skill_name + parameters）
2. 后端做参数校验（见上），再构建 prompt、准备含 `.claude/skills/{skill_name}/` 的工作目录
3. 调用 Claude Agent SDK 的 `query(prompt=user_prompt, options=...)`，SDK 加载 Skill 并自主调用工具完成任务
4. 收集 message 流中的结果，返回给前端
5. 前端根据 ui_config 渲染结果

#### 6. MVP 支持的 UI 类型

| UI 类型    | 用途           | 示例 Skill  |
| ---------- | -------------- | ----------- |
| 对话式交互 | 文本输入/输出  | felo-search |
| 进度展示   | 长时间任务状态 | felo-slides |
| 链接输出   | URL 结果       | felo-slides |

**不支持（后面迭代）：**

- 文件上传/下载
- 数据可视化（图表）
- 画布/编辑器
- 地图/视频

#### 7. 可行性调研与实现方案：参数动态表单 + 返回动态渲染（AI Page）

**能不能做？** 能。在现有「对话 + DynamicUI」上扩展即可，无需推翻重做。

**目标**：skill 参数多时能**动态生成填写页**让用户好写；执行**返回内容**按类型**动态渲染**；整体做成「一个 skill 一个 AI 页」。

---

**怎么做（分步实现）**

**Step 1：约定 metadata 里的参数 schema**

- 在分析阶段（skill_analyzer）让 Claude 多输出 **`parameters`** 数组，写入 metadata，例如：
  ```json
  "parameters": [
    { "name": "video_code", "type": "youtube_video_id", "label": "视频链接或 ID", "required": true, "description": "YouTube 链接或 11 位视频 ID" },
    { "name": "language", "type": "string", "label": "字幕语言", "required": false }
  ]
  ```
- 类型可先支持：`string`、`number`、`url`、`youtube_video_id`（前端可做校验/解析）。
- **涉及**：`backend/app/services/skill_analyzer.py`（prompt 增加 parameters 输出）、`metadata.json` 结构、`frontend/src/types/api.ts` 的 `SkillMetadata` 增加 `parameters?: ParameterSchema[]`。

**Step 2：前端根据 parameters 动态渲染表单**

- 新增组件：`DynamicParamForm`（或放在 Chat 页上方）：根据 `parameters` 渲染输入框/下拉等，收集值为 `Record<string, unknown>`。
- 交互：用户可**只填表**然后点「执行」；或保留现有对话，由 AI 引导填表；或「表单 + 对话」并存（表单预填，对话补充）。
- **涉及**：`frontend/src/components/DynamicParamForm/`（新建）、Chat 页或 ChatPage 引入、执行时把表单值作为 `parameters` 传给 `POST /execute`。

**Step 3：执行返回带 result_format + 结构化数据**

- 后端执行层（execute 路由 + execution_spec / output_presenter）在返回里增加：
  - `result_format`：与 `execution.response.format` 对齐（如 `text`、`url`、`youtube_subtitles`、`answer_sources`）。
  - 可选 `result_data`：结构化数据（如 `subtitles: [{ start, end, text }]`、`sources: [{ title, url }]`），供前端专用组件渲染。
- **涉及**：`backend/app/api/execute.py` 返回结构、`backend/app/services/execution_spec.py` 或 presenter 在 HTTP/plan 执行路径里带上 format 与 data；`frontend/src/types/api.ts` 的 `ExecutionResultPayload` 增加 `result_format?`、`result_data?`。

**Step 4：前端按 result_format 动态渲染结果**

- 在 DynamicUI 中根据 `result_format` 分支：`youtube_subtitles` → 字幕列表/时间轴组件；`answer_sources` → 来源卡片；`url` → LinkOutput；`text`/`markdown` → TextOutput。
- **涉及**：`frontend/src/components/DynamicUI/index.tsx` 及新增子组件（如 `SubtitlesOutput`、`SourcesOutput`）。

**Step 5：收口为「AI Page」布局**

- 页面布局：顶部 skill 描述 → 参数区（DynamicParamForm 或对话）→ 执行按钮/发送 → 结果区（DynamicUI 按 result_format 渲染）。
- 路由可沿用现有 `/chat/:skillName`，仅调整 ChatPage 布局。
- **涉及**：`frontend/src/pages/ChatPage.tsx`、Chat 组件布局。

**建议落地顺序**：Step 1（schema 约定 + 分析器）→ Step 2（动态表单）→ Step 3（返回 result_format/result_data）→ Step 4（结果组件）→ Step 5（布局收口）。可放在当前 MVP 验收后的一轮迭代。

#### 8. 多平台 Skill 接入与自动化适配

**场景**：用户从 Cursor、GitHub、Felo 市场、自建仓库等多渠道下载的 skill，格式/元数据位置可能不同，需要**自动识别来源并适配**为平台统一格式，保证「上传即可用」。

**设计原则**

- **单一 Canonical 格式**：平台内部只认一套 metadata 结构（description、parameters、ui_config、execution）。所有外部格式最终都转换为该结构。
- **先适配、后增强**：能通过「适配器」识别的，优先用适配器产出 canonical；适配器未覆盖或字段缺失时，再用 Claude 分析补全/校验。
- **可扩展**：新增平台时只需新增一个 Adapter 并注册，不改上传主流程。

**适配流程（上传时）**

1. **输入**：SKILL.md 原始内容 + 可选「来源提示」（如 URL、平台名、文件名）。
2. **检测**：按优先级尝试各已注册适配器的 `detect(content, hints)`；第一个返回 True 的适配器进入步骤 3。
3. **转换**：调用该适配器的 `adapt(content, hints)`，得到 canonical 片段（可能只含部分字段）。
4. **合并与补全**：将适配器输出与现有逻辑合并：若未提供 execution/parameters 等，再调用 Claude 分析器补全；若适配器已提供，可选择性用 Claude 做一次校验或增强。
5. **落库**：写入 `metadata.json`（与现有逻辑一致）。

**适配器接口（约定）**

- **detect(content: str, hints?: { url?, source?, filename? }) → bool**  
  判断当前内容是否来自该适配器所代表的平台/格式。
- **adapt(content: str, hints?: ...) → CanonicalFragment**  
  从原始内容（及可选 frontmatter、侧边 JSON 等）解析并输出平台 canonical 片段。  
  `CanonicalFragment` 至少包含：`description?: string`；可选：`parameters?`, `ui_config?`, `execution?`。缺失字段由后续 Claude 分析补全。

**来源检测方式（示例）**

| 方式           | 说明 |
|----------------|------|
| URL 模式       | 上传时若带来源 URL（如 `https://github.com/.../SKILL.md`），可据此选 GitHub 适配器。 |
| 文件名/路径    | 若用户打包上传多文件，目录名或文件名约定（如 `cursor-skill-xxx`）可作 hint。 |
| Frontmatter    | SKILL.md 顶部 `---` 内含 `source: cursor` / `platform: felo` 等，适配器据此识别。 |
| 结构特征       | 如「首行为特定 JSON」「含特定 Markdown 标题结构」等，由各适配器自行实现 detect。 |

**平台与适配器示例**

| 平台/来源     | 检测依据（示例）           | 适配要点 |
|---------------|----------------------------|----------|
| Cursor Rules  | frontmatter 或路径含 cursor | 将 rule 条款映射为 description；无 execution 时依赖 Claude 推断。 |
| Felo / 本平台 | frontmatter 含 felo 或已有 execution 结构 | 若已是 canonical 或子集，直接复用或补全。 |
| 通用 SKILL.md | 标准 YAML frontmatter（description、triggers） | 从 frontmatter 抽 description；parameters 从 triggers/params 解析若存在。 |
| 未知/兜底     | 所有适配器 detect 均 False | 完全依赖现有 Claude 分析器（analyze_skill），保证任意 SKILL.md 都能生成可用 metadata。 |

**实现要点（代码层）**

- **Adapter 注册表**：在内存中维护 `List[SkillAdapter]`，上传时顺序执行 detect，命中则 adapt。
- **CanonicalFragment 类型**：与现有 `metadata.json` 字段对齐（description、parameters、ui_config、execution），适配器只填能填的，其余为 None。
- **上传 API**：保持 `POST /skills/upload` 不变；可选 query/body 增加 `source_hint?: string` 或 `origin_url?: string`，传给 detect/adapt 作 hints。
- **与 analyze_skill 的配合**：`meta = adapter.adapt(...) if detected else {}`，然后 `analyzed = analyze_skill(content)`，最后 `merged = { ...defaults, ...meta, ...analyzed }`（或按字段优先级约定合并），再写入 metadata.json。

**扩展新平台时**

1. 在 `skill_adapters` 包下新增模块，实现 `detect` + `adapt`。
2. 在注册表中 `register(NewPlatformAdapter())`。
3. 无需改动上传、执行、前端逻辑。

### Why This Approach

**为什么选择对话式交互 + 动态 UI？**

- **差异化价值** - 其他平台都是填表单，我们是对话式，更自然
- **降低门槛** - 用户不需要理解参数，AI 引导即可
- **更好的体验** - 动态 UI 让 skills 看起来像真正的产品

**为什么选择 Python + FastAPI？**

- Claude Agent SDK 有 Python 版本，集成方便
- FastAPI 现代、快速，适合 API 开发
- Python 生态丰富，适合 AI 相关开发

**为什么选择文件存储而不是数据库？**

- MVP 阶段快速验证，不需要配置数据库
- 文件存储符合 skills 的文件结构（SKILL.md）
- 版本控制友好（可以用 git）
- 后面可以轻松迁移到数据库

**为什么选择 Monorepo？**

- MVP 阶段代码量不大，放一起方便管理
- 前后端可以共享类型定义
- 部署简单

## Alternatives Considered

### Option A: 只生成表单，不做对话式交互

- **优点**: 实现简单，工作量小
- **缺点**: 用户体验差，没有差异化价值
- **拒绝理由**: 不够 cool，无法吸引用户

### Option B: 支持所有类型的动态 UI（图表、画布、编辑器等）

- **优点**: 功能强大，用户体验好
- **缺点**: 工作量大，MVP 阶段不现实
- **拒绝理由**: 过度设计，先验证核心价值

### Option C: 后端用 Node.js

- **优点**: 前后端语言统一，性能好
- **缺点**: Claude Agent SDK 的 Node.js 支持不如 Python
- **拒绝理由**: Python 更适合 AI 相关开发

### Option D: 使用数据库存储

- **优点**: 查询效率高，扩展性好
- **缺点**: 需要配置数据库，增加复杂度
- **拒绝理由**: MVP 阶段不需要，文件存储足够

## Implementation Checklist

### Phase 1: 基础架构（Week 1）

- [ ] 创建 Monorepo 项目结构
- [ ] 前端：React + TypeScript + Tailwind CSS 脚手架
- [ ] 后端：Python + FastAPI 脚手架
- [ ] 文件存储：实现 skills 的 CRUD 操作
- [ ] API 设计：定义前后端接口
- [ ] **执行方案 POC**：用 Claude Agent SDK 在本地验证「将 `skills/{name}/` 映射为 `.claude/skills/{name}/` + query(prompt, options)」能稳定跑通至少一个 skill（如 felo-search）

### Phase 2: Skills 上传与分析（Week 1-2）

- [ ] 前端：Skills 上传组件
- [ ] 后端：接收并保存 SKILL.md
- [ ] 集成 Claude API：分析 SKILL.md
- [ ] 生成 ui_config（UI 类型、参数定义）
- [ ] 前端：Skills 列表展示

### Phase 3: 对话式交互（Week 2-3）

- [ ] 前端：对话界面组件（类似 ChatGPT）
- [ ] 后端：对话接口（接收用户消息，返回 AI 回复）
- [ ] 集成 Claude API：引导用户提供参数
- [ ] 参数收集逻辑（对话式）
- [ ] 前端：消息渲染（Markdown 支持）

### Phase 4: 动态 UI（Week 3）

- [ ] 前端：进度条组件
- [ ] 前端：链接输出组件
- [ ] 前端：文本输出组件（Markdown）
- [ ] 前端：根据 ui_config 动态渲染
- [ ] 后端：返回 UI 配置给前端

### Phase 5: Skills 执行（Week 3-4）

- [ ] 集成 Claude Agent SDK（Python）
- [ ] 后端：执行 skills 接口
- [ ] 后端：处理长时间任务（进度更新）
- [ ] 前端：轮询任务状态（felo-slides）
- [ ] 错误处理和重试逻辑

### Phase 6: 验证与测试（Week 4）

- [ ] 导入 felo-skills 仓库的两个 skills
- [ ] 测试 felo-search（对话式搜索）
- [ ] 测试 felo-slides（进度展示 + 链接输出）
- [ ] 修复 bug 和优化体验
- [ ] 部署到测试环境

### Phase 7: 部署（Week 4）

- [ ] 前端部署到 Vercel/Netlify
- [ ] 后端部署到云服务器
- [ ] 配置域名和 HTTPS
- [ ] 监控和日志

## Open Questions

### 0. Skill 所需 API Key / Token（MVP 需约定）

- **问题**：felo-search、felo-slides 等若依赖外部 API Key 或 Token，存放位置与访问方式未定义。
- **建议**：MVP 仅通过**后端环境变量或密钥服务**注入，不写进代码、不落库、不随 skill 内容或日志输出；设计文档与实现中明确「哪些 key 由谁配置」。
- **决策时机**：Phase 2 前与 Phase 5 实现前确认。

### 1. 安全性问题（后面迭代）

- **问题**: Skills 可以执行任意 CLI 命令，如何防止恶意代码？
- **可能方案**:
  - 容器隔离（Docker/K8s）
  - 沙箱执行（Firecracker、gVisor）
  - 白名单 CLI（只允许安全命令）
  - 人工审核 + 容器隔离
- **决策时机**: V2 迭代时讨论

### 2. 数据库迁移（后面迭代）

- **问题**: 文件存储扩展性差，何时迁移到数据库？
- **可能方案**: PostgreSQL + SQLAlchemy
- **决策时机**: 用户数 > 100 或 skills 数 > 50 时

### 3. 用户认证（后面迭代）

- **问题**: 如何管理用户和权限？
- **可能方案**:
  - OAuth（GitHub、Google）
  - 自建用户系统
- **决策时机**: V2 迭代时讨论

### 4. Skills 市场（后面迭代）

- **问题**: 如何让创作者发布、分享、甚至售卖 skills？
- **可能方案**:
  - 公开/私有 skills
  - 评分和评论
  - 付费 skills（Stripe 集成）
- **决策时机**: V3 迭代时讨论

### 5. 更多 UI 类型（后面迭代）

- **问题**: 何时支持图表、画布、编辑器等复杂 UI？
- **可能方案**:
  - 图表：ECharts/Recharts
  - 画布：Fabric.js/Konva
  - 编辑器：Monaco Editor/CodeMirror
- **决策时机**: 根据用户反馈决定优先级

## 后续迭代规划

> 基于当前 MVP + 参数/动态表单/result_format/AI Page/多平台适配器骨架 的完成情况，建议按以下阶段迭代。

### 当前已完成（可视为 MVP+）

- 上传/列表/对话/执行（SDK 主路径 + execution 回退）
- 参数 schema + 动态表单（DynamicParamForm）+ 填表即执行
- 执行返回 result_format + result_data，DynamicUI 按格式渲染（字幕、来源、链接、文本）
- AI Page 布局：描述 + 参数区 + 对话/结果区
- 多平台适配器骨架（Frontmatter 适配器 + 上传时 try_adapt → 与 analyze_skill 合并）
- Windows 启动说明（run_win.py）

### V1：体验与扩展（建议下一轮）

| 方向 | 内容 | 优先级 |
|------|------|--------|
| **多平台适配** | 增加 Cursor / GitHub / 通用 SKILL 等适配器，完善 detect/adapt；上传 API 支持 source_hint、origin_url 透传 | 高 |
| **参数与校验** | 执行前按 metadata.parameters 做必填、类型、长度等校验；表单支持默认值、placeholder 与错误提示 | 高 |
| **result_format 扩展** | 新增 execution.response.format 类型（如 web_extract 结构化摘要），对应 _extract_result_data + 前端组件 | 中 |
| **体验打磨** | 执行中 loading、错误态与重试、空状态文案；移动端布局；可选「表单 / 对话」切换 | 中 |
| **文档与配置** | README/design-mvp 与实现状态同步；API Key 配置说明（哪些 skill 需哪些 key）集中写清 | 低 |

### V2：安全与规模

- **安全**：执行隔离（容器/沙箱或白名单 CLI）、skill 审核策略（见 Open Questions 1）。
- **数据**：用户/技能数上来后引入数据库（见 Open Questions 2）；metadata 与执行记录可持久化。
- **认证**：如需多租户或「我的 skills」，接入 OAuth 或自建登录（见 Open Questions 3）。

### V3：生态与商业化（可选）

- **Skills 市场**：公开/私有、评分、付费等（见 Open Questions 4）。
- **更多 UI 类型**：图表、画布、编辑器等（见 Open Questions 5）。

**建议**：先做完 V1 的「多平台适配 + 参数校验 + 1～2 个 result_format 扩展」，再根据使用反馈决定是否进入 V2（安全/数据/认证）。

## References

- [Claude Agent SDK - Overview](https://platform.claude.com/docs/en/agent-sdk/overview)
- [Claude Agent SDK - Skills](https://platform.claude.com/docs/en/agent-sdk/skills)
- [Claude Agent SDK - Python](https://platform.claude.com/docs/en/agent-sdk/python)（API 参考）
- [claude-agent-sdk (PyPI)](https://pypi.org/project/claude-agent-sdk/)
- [felo-skills Repository](https://github.com/Felo-Inc/felo-skills)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [React Documentation](https://react.dev/)

---

## 实现符合度（与当前代码对齐）

> 最后核对：2026-03-07

### 需求点清单

| #   | 需求点                | 状态    | 说明                                                                                                                                         |
| --- | --------------------- | ------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | 上传/获取 skill       | ✅      | 有上传（POST /skills/upload）、列表（GET /skills）；上传后固定生成 metadata，无 Claude 分析                                                  |
| 2   | 有界面                | ✅      | SkillList → 选 skill → ChatPage 对话页                                                                                                       |
| 3   | 填写方式 = 交互式对话 | ✅      | 对话引导，`ready_to_execute` + `parameters` 后调 `/execute`                                                                                  |
| 4   | 可选：简单表单        | ⚠️ 未做 | 仅对话，无表单兜底（设计为可选）                                                                                                             |
| 5   | 代为执行              | ✅      | execute.py：临时目录映射 + Agent SDK；无 CLI 时 Felo 直连 / Messages API 回退                                                                |
| 6   | 结果展示              | ⚠️ 部分 | 有 TextOutput/LinkOutput/ProgressBar 与 DynamicUI；执行结果目前当纯文本/Markdown 展示，未按 ui_config 走 DynamicUI（如 url 未用 LinkOutput） |

### 架构差异（相对设计文档）

- **未单独实现**：`skill_analyzer.py`、`ui_generator.py`、`agent_executor.py`、`file_storage.py`；逻辑合并进 `skills.py`、`execute.py`、`skill_loader.py`。
- **已有且符合**：`skills.py`（CRUD/上传）、`chat.py`（对话 + 工具/READY_TO_EXECUTE）、`execute.py`（工作区准备 + SDK + Felo 回退）、`skill_loader.py`、`config_store.py` + config API（API Key 注入）。

### 设计文档中的 Blocker / 要求

- **对话 → 执行协议**：✅ 已实现（`ready_to_execute`、`parameters`、前端自动调 `/execute`）。
- **执行前参数校验**：⚠️ 未做：仅取 `prompt`/`query`，未按 skill 的 parameters schema 做类型/必填/长度校验（设计 5. 执行 Skills 要求）。
- **API Key**：✅ 后端 .env + 对话中 save_config 写入，符合 Open Question 0 建议。

### 建议的后续补齐（优先级）

1. **结果展示**：执行返回 `url`/`progress` 时，前端按当前 skill 的 `ui_config` 用 DynamicUI 渲染（LinkOutput/ProgressBar），而不是仅把 content 当消息文本。
2. **参数校验**：在执行前对 `parameters` 做基本校验（必填、类型），与 skill 分析结果一致（若引入 skill 分析则用其 schema）。
3. **（可选）Skill 分析**：上传时用 Claude 分析 SKILL.md 生成 description、ui_config、parameters，替代固定「上传的 Skill」与固定 ui_config。
