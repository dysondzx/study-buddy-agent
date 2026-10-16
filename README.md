# 学伴智能体助手（study-buddy-agent）

基于 **LangGraph + LangChain 1.x + FastAPI** 的个人成长操作系统：3 个 Agent 协作，整合三种检索/查询能力，前端为 React + Vite 的流式对话界面，并内置 RAGAS 评估（命令行 + HTTP 两种用法）。

| Agent | 职责 | 工具集（底层能力） |
|-------|------|---------|
| 📋 **规划师** | 拆解目标、排日程、分配任务 | `knowledge_graph_query`（GraphRAG 依赖分析）+ `query_study_data`（Text2SQL 历史节奏） |
| 📚 **知识管家** | 检索笔记、关联知识点 | `knowledge_search`（Vector RAG：BGE + Chroma）+ `knowledge_graph_query`（GraphRAG） |
| 📊 **追踪者** | 记录学习、打卡、统计 | `record_study` / `record_habit`（写入）+ `query_study_data`（Text2SQL 统计） |

- 每个 Agent 由 `langchain.agents.create_agent` 构建（`recursion_limit=12`），按需自主调用工具。
- 编排层：`router`（关键词打分，零 LLM 开销）→ 单 Agent 或 hybrid 串行三路 → `synthesizer` 用 LLM 合成并**流式**输出。
- 会话历史持久化到 SQLite（`conversations` / `messages`），由服务端在首轮消息时自动建会话、自动生成标题。

## 快速开始

### 1. 后端

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env             # 填写 DEEPSEEK_API_KEY
```

```bash
# 初始化：SQLite 建表（应用启动时也会幂等执行一次）
python -m app.data.init_db

# 构建 Chroma 向量索引（把 Markdown 笔记放到 backend/notes/ 下）
python -m app.data.build_index

# 启动
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

验证：`curl http://localhost:8000/health` → `{"status":"ok"}`

> 首次调用 embedding 模型会下载 `BAAI/bge-small-zh-v1.5`；`notes/` 为空时索引为空，`knowledge_search` 会如实提示"知识库尚未初始化"。

### 2. 前端

```bash
cd frontend
npm install
npm run dev      # http://localhost:5173（Vite proxy 把 /api 转发到 :8000）
```

界面能力：会话列表（新建/切换/删除）、SSE 流式打字、按会话加载历史、流式期间锁定交互。

### 3. 评估（命令行）

```bash
cd backend
python -m app.evaluation.run_eval                      # 全量样本 + 全部指标
python -m app.evaluation.run_eval --metrics faithfulness,answer_relevancy
python -m app.evaluation.run_eval --limit 3
```

## 架构

```
用户问题（POST /api/chat）
   │
   ▼
┌──────────────────────────────────────────────┐
│ Router（意图路由：关键词计数，不消耗 LLM）      │
└──┬──────────┬──────────┬───────────┬─────────┘
   ▼          ▼          ▼           ▼
 planner   knowledge   tracker     hybrid
   │          │          │           │
   │          │          │      planner → knowledge → tracker（串行三路）
   ▼          ▼          ▼           ▼
┌──────────────────────────────────────────────┐
│ Synthesizer（LLM 合成：结论 → 依据 → 建议）     │
└──────────────────────────────────────────────┘
   │
   ▼
SSE 流式返回（仅转发 synthesizer 节点的 token）
```

**路由规则**：命中关键词打分最高的单一维度 → 直达对应 Agent；最高分为 0（无命中）或出现并列 → `hybrid`。
关键词表见 `app/agents/orchestrator.py`（如 计划/安排/目标、笔记/学过/错题、打卡/记录/多少小时）。

**状态图节点**：`router → planner|knowledge|tracker → synthesizer → END`
（hybrid 时条件边串联 `planner → knowledge → tracker → synthesizer`；单意图时各分支直接进 `synthesizer`）

**技术栈**：LangGraph（状态机 + 条件边） / LangChain 1.x `create_agent` / DeepSeek（ChatOpenAI 兼容） / BGE + Chroma / NetworkX 知识图谱 / SQLite + Text2SQL / RAGAS 0.4.3 / React + Vite

## 接口一览

### 对话

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/chat` | 请求体 `{message, conversation_id?}`，返回 SSE 流。`conversation_id` 为空表示新会话，服务端就地创建 |
| GET | `/api/conversations` | 会话列表（按 `updated_at` 倒序） |
| GET | `/api/conversations/{id}` | 会话详情，含全部历史消息 |
| DELETE | `/api/conversations/{id}` | 删除会话及其消息 |
| GET | `/health` | 健康检查 |

**SSE 事件协议**（`data: {...}\n\n`）：

| type | 载荷 | 含义 |
|------|------|------|
| `meta` | `conversation_id` | 每个请求开头下发，首轮新建时前端据此归位 |
| `message` | `content` | 正文增量 token |
| `error` | `content` | 编排异常（已有部分内容时前端保留已收到的文本） |
| `done` | — | 结束标记 |

用户消息在编排开始前先落库，助手回复在 `finally` 中落库（客户端中途断开也不会丢），保证历史与界面一致。

### 评估（HTTP）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/eval/health` | 数据集大小 + 运行中的任务数 |
| POST | `/api/eval/run` | 请求体 `{limit?, metrics?}`，异步启动评估，返回 `task_id` |
| GET | `/api/eval/run/{task_id}` | 轮询任务状态：`pending` / `running` / `success` / `failed` |

任务状态保存在进程内存中（`_TASKS`），重启即失效。

## 数据与持久化

| 存储 | 位置（默认/环境变量） | 内容 |
|------|----------------------|------|
| SQLite | `SQLITE_PATH` | `study_log` / `habit_checkin` / `learning_goals`（学习数据，含示例数据）+ `conversations` / `messages`（对话历史） |
| Chroma | `CHROMA_PATH` | 笔记向量索引（`notes/**/*.md` 切块，chunk 500 / overlap 50） |
| 知识图谱 | `KG_PATH` | NetworkX 有向图 pickle；存在即复用，不存在则按内置三元组构建后落盘 |

图谱边语义：`A --PREREQUISITE--> B` 表示"学 B 之前需要先懂 A"，另有 `RELATED` 关联边；查询工具支持 N 跳（默认 2 跳）遍历并序列化为文本。

## 依赖版本锁定

```
langchain>=1.0.0 / langchain-core>=1.0.0 / langchain-classic>=0.1.0
langchain-community==0.4.1   # 必须 0.4.1，0.4.2 与 ragas 冲突
ragas==0.4.3
openai==2.54.0
instructor==1.16.0
```

评估指标：`faithfulness`、`answer_relevancy`、`context_precision`、`context_recall`、`answer_correctness`（后三者需要样本带 `reference`；自定义数据集改 `app/evaluation/__init__.py` 的 `DEFAULT_DATASET`）。

## Docker 部署

```bash
# 1. 填 Key（compose 读取 backend/.env）
cp backend/.env.example backend/.env

# 2. 构建前端静态资源（nginx 挂载 frontend/dist）
cd frontend && npm run build && cd ..

# 3. 启动（backend + nginx，80 端口）
docker compose --profile prod up -d --build

# 校验
docker compose exec nginx nginx -t
curl http://localhost/
```

- backend 镜像启动命令会先跑 `init_db`、`build_index` 再起 `uvicorn`（2 workers），因此容器内无需手动初始化。
- 数据落 `agent-data` 卷（挂到容器 `/data`），compose 已显式覆盖 `SQLITE_PATH` / `CHROMA_PATH` / `KG_PATH` 为 `/data/...`。
- nginx 对 `/api/` 关闭 `proxy_buffering` 等缓冲以保证 SSE 流式；`nginx` 服务仅在 `prod` profile 下启动。
- `docker-compose.yml` 须在项目根目录执行，所有路径以其为基准。

## 目录结构

```
study-buddy-agent/
├── backend/
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── .env.example
│   ├── notes/                    # 笔记语料（learning-notes.md 为示例）
│   ├── store/                    # 本地开发时的 SQLite / Chroma / 图文件落盘目录
│   └── app/
│       ├── main.py               # FastAPI 入口 + lifespan（启动时幂等建表）+ CORS
│       ├── config.py             # Settings / JSON 日志 / get_llm 工厂
│       ├── api/
│       │   ├── chat.py           # SSE 流式 /api/chat（编排 + 落库）
│       │   ├── conversations.py  # 会话列表/详情/删除
│       │   └── evaluation.py     # /api/eval/*（内存任务登记）
│       ├── agents/
│       │   ├── planner.py        # 规划师（create_agent + 2 工具）
│       │   ├── knowledge.py      # 知识管家（create_agent + 2 工具）
│       │   ├── tracker.py        # 追踪者（create_agent + 3 工具）
│       │   └── orchestrator.py   # 关键词路由 + LangGraph 状态图
│       ├── tools/
│       │   ├── knowledge_base.py # Vector RAG 检索（懒加载 Chroma）
│       │   └── study_db.py       # SQLDatabaseToolkit 的 Text2SQL 子 Agent + 写入工具
│       ├── data/
│       │   ├── init_db.py        # SQLite 建表 + 示例数据（可 __main__ 直接执行）
│       │   ├── build_index.py    # Chroma 索引构建（可 __main__ 直接执行）
│       │   ├── knowledge_graph.py# 图谱构建 / 遍历 / 序列化 / 查询工具
│       │   └── conversations.py  # 会话与消息的持久化层
│       └── evaluation/
│           ├── __init__.py       # EvalSample + DEFAULT_DATASET + 裁判 LLM/Embedding 工厂
│           ├── runner.py         # 逐样本跑编排 + 逐指标打分
│           └── run_eval.py       # 命令行入口
├── frontend/
│   ├── index.html
│   ├── package.json / vite.config.ts / tsconfig.json
│   └── src/
│       ├── App.tsx               # 会话状态编排（发送、切换、删除）
│       ├── main.tsx
│       ├── api/client.ts         # fetch + ReadableStream 解析 SSE
│       ├── types/chat.ts         # ChatMessage / SSEData / Conversation*
│       ├── components/           # Sidebar / ChatWindow / MessageList / MessageItem / InputBar
│       └── styles/app.css
├── nginx/nginx.conf              # 静态资源 + /api 反代（SSE 关闭缓冲）
└── docker-compose.yml            # backend（+ prod profile 下的 nginx）
```

## 配置项

| 变量 | 默认值（`config.py`） | 说明 |
|------|----------------------|------|
| `DEEPSEEK_API_KEY` | — | 必填 |
| `DEEPSEEK_BASE_URL` | `https://api.deepseek.com/v1` | OpenAI 兼容地址 |
| `DEEPSEEK_MODEL` | `deepseek-chat` | 对话模型 |
| `EMBEDDING_MODEL` | `BAAI/bge-small-zh-v1.5` | 向量模型（CPU + 归一化） |
| `SQLITE_PATH` | `/data/agent_data.db` | 本地开发建议用 `./store/agent_data.db` |
| `CHROMA_PATH` | `/data/chroma_notes` | 同上 |
| `KG_PATH` | `/data/knowledge_graph.pkl` | 同上 |
| `NOTES_DIR` | `./notes` | 笔记目录 |
