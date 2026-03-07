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
3. 在对话里输入需求（如「搜索 苏州天气」「生成 React 入门 PPT」），Claude 会引导并在意图明确时执行该 skill（执行阶段使用 Claude Agent SDK 在临时工作区加载 SKILL.md 并跑工具）

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
