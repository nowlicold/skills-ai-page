# Skills 使用平台 (MVP)

让小白用户通过 Web 上传并使用 Claude Code / OpenClaw 的 skills，无需安装命令行工具。

技术栈：**前端** React + TypeScript + Tailwind CSS + shadcn/ui；**后端** FastAPI + **Claude（Anthropic Messages API 对话 + Claude Agent SDK 执行）**。

## 快速开始

### 0. 配置 Claude API Key（必做）

后端需要 Anthropic API Key 才能使用真实对话与执行：

1. 在 [Anthropic Console](https://console.anthropic.com/) 创建 API Key。
2. 在 `backend` 目录下新建 `.env` 文件（可复制 `.env.example`）：
   ```
   ANTHROPIC_API_KEY=sk-ant-你的key
   ```
3. 重启后端服务。

### 1. 前端

```bash
cd frontend
npm install
npm run dev
```

浏览器打开 http://localhost:5173

### 2. 后端（供前端联调）

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate   # Windows
# source .venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
# Windows 必须用 run_win.py（先设 Proactor 再起 uvicorn，单进程无 reload）
python run_win.py                  # Windows（在 backend 目录下）
# uvicorn app.main:app --reload   # macOS/Linux
```

若后端不在本机 8000 端口，在 `frontend` 下新建 `.env`：

```
VITE_API_URL=http://你的后端地址:8000
```

#### Windows 后端启动说明（必读）

在 Windows 上，若用 `uvicorn app.main:app --reload` 启动，执行 skill 时会报 **`Failed to start Claude Code: NotImplementedError`**。原因：

- 使用 `--reload` 时 uvicorn 会起**子进程**跑服务，子进程不会先执行 `main.py` 里的事件循环设置。
- Windows 默认的 **SelectorEventLoop** 不支持子进程，必须用 **ProactorEventLoop**（在创建事件循环之前设置 `WindowsProactorEventLoopPolicy()`）。

**正确做法**：在 Windows 上**不要用** `uvicorn ... --reload`，改用项目提供的脚本（单进程、先设策略再起 uvicorn）：

```bash
cd backend
.venv\Scripts\activate
python run_win.py
```

改代码后需重启时，先 Ctrl+C 停掉再重新执行 `python run_win.py` 即可。详见 [design-mvp.md](./design-mvp.md) 中的「Windows 已知问题」。

### 3. 使用流程

1. **首页**：上传 SKILL.md（或查看已有 skills）
2. 点击某个 skill 的「使用这个 skill」→ 进入对话页
3. **两种使用方式**（可同时用）：
   - **对话**：在底部输入框输入需求（如「搜索 苏州天气」），AI 引导并在意图明确时自动执行
   - **填表执行**：若该 skill 有「填写参数」区域，直接填好参数后点「执行」即可（适合已知参数的场景）
4. 执行结果会按类型展示：文本、链接、字幕列表、参考来源等

### 4. 上传 Skill 的几种方式

- **本地上传**：在首页点上传，选择本地的 `.md` 文件（如 SKILL.md）
- **多平台适配**：若文件来自其他平台（如 Cursor、GitHub），上传后系统会先尝试按格式识别并转换元数据，再结合 Claude 分析补全；可选在调用上传 API 时传 `source_hint` 或 `origin_url` 帮助识别

### 5. 可选配置

- **Felo 类 Skill**（搜索、PPT、字幕等）：若 skill 的 execution 里用到 Felo API，需在 `backend/.env` 中配置 `FELO_API_KEY=你的 key`，否则 HTTP 回退执行会报错。
- **仅用 CLI 执行**：若你已安装 Claude Code CLI 且希望「无 CLI 就报错、不自动回退」，可在前端或请求里传 `execution_mode: "sdk_only"`（默认会先尝试 CLI，失败再回退到服务端 execution）。

## 项目结构

```
skills-ai-page/
├── frontend/          # React + Vite + shadcn + Tailwind
│   ├── src/
│   │   ├── components/   # SkillList, SkillUpload, Chat, DynamicUI
│   │   ├── pages/        # Home, ChatPage
│   │   ├── store/        # Zustand: useSkillsStore, useChatStore
│   │   ├── lib/          # api, utils
│   │   └── types/
│   └── package.json
├── backend/           # FastAPI
│   ├── app/
│   │   ├── api/         # skills, chat, execute
│   │   └── main.py
│   ├── skills/          # 上传的 SKILL.md 存放目录
│   └── requirements.txt
└── design-mvp.md      # 设计文档
```

## 设计文档

详见 [design-mvp.md](./design-mvp.md)。
