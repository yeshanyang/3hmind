# 3hmind v3.0 — 统一自我成长智能体

> 基于5层认知架构的AI个人成长教练，帮助用户进行目标管理、技能发展、职业规划、情绪觉察和深度反思。

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## 特性

### 5层认知管线
项目概述 — 5层认知架构说明
核心能力 — 多用户、语义记忆、8大主题域、深度追问、语音交互等13项特性
技术栈 — 完整的后端/前端/基础设施技术清单
项目结构 — 全目录树带注释
快速开始 — 本地运行与Docker部署步骤
配置说明 — 全部20+环境变量详解
API概览 — 30+路由分6类列出
数据库设计 — 8张表结构与关键字段
架构说明 — v3重构阶段说明与兼容策略


| 层 | 模块 | 功能 |
|---|------|------|
| **第1层：输入** | `input_layer/` | 多模态输入标准化（文本、语音、文档、视频、摄像头） |
| **第2层：意图** | `intent_layer/` | 二层意图解析（表层命令 + LLM深层动机推断），6种成长场景模板 |
| **第3层：记忆/思维** | `mind_layer/` | 统一认知记忆（SQLite + ChromaDB向量库 + 主题记忆） |
| **第4层：调度** | `dispatch_layer/` | 任务调度与思维引导（拆解、利弊分析、复盘、规划） |
| **第5层：输出** | `output_layer/` | 自适应多模态输出（文本/语音/展示） |

### 核心能力

- **多用户支持** — JWT认证 + 按用户数据隔离（每用户独立 SQLite + ChromaDB）
- **LLM深度推理** — 接入DeepSeek/OpenAI兼容API，进行根因分析、成长规划与反思
- **语义记忆检索** — 基于ChromaDB向量存储的相似记忆检索，嵌入维度1536
- **8大主题记忆域** — 技术架构、职业成长、深度思考、学习方法、健康、人际关系、日常生活、英语学习，自动检测与归类
- **深度追问模式** — 生成4-6个递进式追问，进行结构化深度教练对话
- **6种成长场景模板** — 目标拆解、情绪觉察、习惯管理、决策辅助、学习路径、职业导航
- **进度追踪** — 活跃目标监控、停滞检测与达成庆祝
- **自动排程** — 后台线程定时反思（60分钟）与轻推（120分钟）
- **SSE流式响应** — Server-Sent Events 实时逐token输出
- **语音交互** — 浏览器录音 → Whisper兼容API转写 + 浏览器TTS朗读回复
- **前端模块化** — SPA 按职责拆分为 7 个独立 JS 模块 (state/api/auth/ui/voice/chat/app) + 独立 CSS，index.html 从 82KB 精简至 10KB
- **个人仪表盘** — 展示个人画像、目标、能力、差距、洞察与主题记忆
- **画像自动提取** — 新用户默认「全栈工程师 / 持续学习成长中」，首次对话后 LLM 从对话中自动提取真实角色、情境、情绪状态、目标与能力，持续优化
- **记忆整合** — 对话记录达到阈值后自动整合为洞察
- **专家评估系统** — 目标4维打分（知识掌握/学习进度/复盘迭代/深度思考），规则引擎+LLM辅助，学习闭环（基线→学习→追问→反馈→验证→迭代），LLM领域知识分析与具体改进建议

## 技术栈

| 层级 | 技术 |
|------|------|
| **后端语言** | Python 3.8+ |
| **Web框架** | FastAPI |
| **ASGI服务** | Uvicorn |
| **LLM API** | OpenAI兼容接口（默认 DeepSeek `deepseek-v4-pro`） |
| **语音转文字** | OpenAI兼容Whisper API（默认阿里云DashScope `qwen3-tts-vd-2026-01-26`） |
| **数据库** | SQLite（8张表） |
| **向量数据库** | ChromaDB |
| **嵌入模型** | 通过LLM API（默认1536维） |
| **认证** | JWT（python-jose）+ bcrypt密码哈希 |
| **用户存储** | JSON文件（`data/users.json`） |
| **前端** | 原生 JS + HTML + CSS（SPA单页应用） |
| **容器化** | Docker + Docker Compose + Docker构建规范 |
| **反向代理** | Caddy（HTTPS + 域名路由） |
| **配置管理** | `.env` + pydantic-settings |

## 项目结构

```
3hmind/
├── main.py                     # 入口 — 启动Web服务与后台调度
├── agent.py                    # UnifiedAgent — 5层管线协调器
├── config.py                   # 配置管理 (pydantic-settings / .env)
├── auth.py                     # JWT认证与用户管理 (bcrypt)
├── scheduler.py                # 后台自主调度器 (定时反思/轻推)
├── requirements.txt            # Python依赖
├── Dockerfile                  # 生产环境Docker镜像
├── docker-compose-new.yml      # 全栈部署 (Caddy + 应用)
├── Caddyfile-new               # Caddy反向代理配置
│
├── input_layer/                # 第1层：多模态输入
│   ├── input_parser.py         #   统一输入标准化器
│   └── document_processor.py   #   文件上传处理器
│
├── intent_layer/               # 第2层：深层意图解析
│   ├── intent_parser.py        #   二级意图解析器
│   ├── growth_templates.py     #   6种成长场景模板
│   └── ambiguity_detector.py   #   模糊输入检测与澄清
│
├── mind_layer/                 # 第3层：统一认知记忆
│   ├── memory_orchestrator.py  #   中央记忆协调器
│   ├── database.py             #   SQLite数据访问层
│   ├── vector_kb.py            #   ChromaDB向量知识库
│   ├── topic_memory.py         #   主题分类长期记忆
│   ├── topic_definitions.py    #   8个主题域定义
│   ├── user_profile.py         #   用户画像CRUD
│   └── session_memory.py       #   会话上下文缓冲
│
├── dispatch_layer/             # 第4层：任务调度与思维引导
│   ├── dispatcher.py           #   意图驱动任务调度
│   ├── thinking_guide.py       #   LLM思维脚手架
│   ├── progress_tracker.py     #   目标进度监控
│   └── assessment_engine.py    #   专家评估引擎（4维打分+LLM领域知识分析）
│
├── output_layer/               # 第5层：自适应输出
│   ├── output_adapter.py       #   格式适配
│   └── response_builder.py     #   统一响应构建
│
├── reasoning/                  # LLM推理引擎
│   └── reasoning_layer.py      #   核心LLM调用
│
├── web/                        # Web层
│   ├── app.py                  #   FastAPI工厂
│   ├── routes.py               #   全部API路由 (30+)
│   └── static/
│       ├── index.html          #   SPA前端
│       ├── css/style.css       #   样式
│       └── js/
│           ├── api.js          #   API客户端
│           ├── auth.js         #   登录/注册/登出
│           ├── state.js        #   全局状态管理
│           ├── ui.js           #   UI渲染与仪表盘
│           ├── voice.js        #   语音识别 + TTS
│           ├── chat.js         #   对话逻辑与流式输出
│           └── app.js          #   应用初始化与轮询
│
└── data/                       # 运行时数据 (gitignore)
    └── {username}/             #   每用户独立数据库
```

## 快速开始

### 环境要求

- Python 3.8+
- OpenAI兼容API Key（推荐 DeepSeek）
- （可选）Docker

### 本地运行

```bash
# 1. 克隆项目
git clone https://github.com/yeshanyang/3hmind.git
cd 3hmind

# 2. 创建虚拟环境
python -m venv .venv
source .venv/bin/activate   # Linux/Mac
# .venv\Scripts\activate    # Windows

# 3. 安装依赖
pip install -r requirements.txt

# 4. 配置环境变量
cp .env.example .env
# 编辑 .env，填入 LLM_API_KEY、JWT_SECRET_KEY、DEFAULT_ADMIN_PASSWORD

# 5. 启动
python main.py
# 访问 http://localhost:8080
```

### Docker部署

```bash
# 单容器
docker build -t 3hmind:latest .
docker run -p 8080:8080 --env-file .env -v ./data:/app/data 3hmind:latest

# 全栈部署（含Caddy反向代理）
docker compose -f docker-compose-new.yml up -d
```

## 配置说明

`.env` 文件中的核心环境变量：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `LLM_API_KEY` | *必填* | LLM API密钥 |
| `LLM_BASE_URL` | `https://api.deepseek.com/v1` | LLM API地址 |
| `LLM_MODEL` | `deepseek-v4-pro` | 模型名称 |
| `LLM_MAX_TOKENS` | `1024` | 最大响应token数 |
| `LLM_TEMPERATURE` | `0.7` | LLM温度 |
| `STT_MODEL` | `qwen3-tts-vd-2026-01-26` | 语音转文字模型 |
| `EMBEDDING_MODEL` | `deepseek-v4-pro` | 嵌入模型 |
| `EMBEDDING_DIM` | `1536` | 嵌入向量维度 |
| `HOST` | `0.0.0.0` | 服务地址 |
| `PORT` | `8080` | 服务端口 |
| `JWT_SECRET_KEY` | *必填* | JWT签名密钥 |
| `JWT_EXPIRE_DAYS` | `30` | Token过期天数 |
| `DEFAULT_ADMIN_PASSWORD` | *必填* | 首次启动管理员密码 |
| `AUTO_REFLECT_INTERVAL_MIN` | `60` | 自动反思间隔（分钟） |
| `AUTO_NUDGE_INTERVAL_MIN` | `120` | 自动轻推间隔（分钟） |
| `CONSOLIDATE_THRESHOLD` | `30` | 触发记忆整合的对话条数 |
| `DATA_DIR` | `data` | 用户数据存储目录 |
| `USERS_FILE` | `data/users.json` | 用户凭证文件 |

## API概览

所有API前缀为 `/`，认证方式为 Bearer Token (JWT)。

### 认证

| 方法 | 路径 | 认证 | 说明 |
|------|------|------|------|
| `POST` | `/api/auth/register` | 否 | 注册新用户 |
| `POST` | `/api/auth/login` | 否 | 登录获取JWT |
| `GET` | `/api/auth/me` | 是 | 获取当前用户信息 |

### 对话与推理

| 方法 | 路径 | 认证 | 说明 |
|------|------|------|------|
| `POST` | `/api/chat` | 是 | 发送消息并获取分析 |
| `POST` | `/api/chat/stream` | 是 | SSE流式对话 |
| `POST` | `/api/review` | 是 | 触发反思 |
| `POST` | `/api/plan` | 是 | 生成成长计划 |
| `POST` | `/api/nudge` | 是 | 获取轻推/检查 |
| `POST` | `/api/proactive/question` | 是 | 生成AI追问 |

### 深度追问

| 方法 | 路径 | 认证 | 说明 |
|------|------|------|------|
| `POST` | `/api/inquiry/start` | 是 | 开启深度追问会话 |
| `POST` | `/api/inquiry/next` | 是 | 回答追问问题 |
| `GET` | `/api/inquiry/status` | 是 | 获取追问会话状态 |
| `POST` | `/api/inquiry/stop` | 是 | 结束追问会话 |

### 仪表盘与画像

| 方法 | 路径 | 认证 | 说明 |
|------|------|------|------|
| `GET` | `/api/dashboard` | 是 | 获取个人仪表盘 |
| `GET/POST` | `/api/profile` | 是 | 获取/更新用户画像 |
| `GET` | `/api/profile/status` | 是 | 检查画像完整度 |
| `GET` | `/api/profile/discover` | 是 | 获取探索性问题 |
| `GET/POST` | `/api/goals` | 是 | 列出/添加目标 |
| `POST` | `/api/goals/{id}/assess` | 是 | 对目标执行专家评估 |
| `GET` | `/api/goals/{id}/assessment` | 是 | 获取目标评估历史 |
| `POST` | `/api/goals/{id}/assess/verify` | 是 | 验证环节（对比基线） |
| `POST` | `/api/goals/{id}/learn/start` | 是 | 开启学习环节 |
| `POST` | `/api/goals/{id}/learn/answer` | 是 | 提交学习回答 |
| `GET` | `/api/goals/{id}/trend` | 是 | 获取进度趋势 |
| `GET/POST` | `/api/abilities` | 是 | 列出/添加能力 |
| `GET` | `/api/poll` | 是 | 轮询自主消息 |
| `GET` | `/api/status` | 是 | 获取Agent状态概览 |

### 上传与语音

| 方法 | 路径 | 认证 | 说明 |
|------|------|------|------|
| `POST` | `/api/upload/document` | 是 | 上传文档 |
| `POST` | `/api/upload/audio` | 是 | 上传音频 |
| `POST` | `/api/upload/video` | 是 | 上传视频 |
| `POST` | `/api/upload/camera` | 是 | 上传摄像头捕获 |
| `POST` | `/api/stt` | 是 | 语音转文字 |
| `GET` | `/api/uploads/history` | 是 | 上传历史记录 |

### 主题记忆

| 方法 | 路径 | 认证 | 说明 |
|------|------|------|------|
| `GET` | `/api/topics` | 是 | 列出所有主题记忆 |
| `GET` | `/api/topics/search?q=` | 是 | 搜索主题记忆 |
| `GET` | `/api/topics/{slug}` | 是 | 获取主题详情 |
| `POST` | `/api/topics/optimize` | 是 | 优化主题记忆（去重） |
| `POST` | `/api/topics/priority` | 是 | 设置主题优先级 |

## 数据库设计

每用户在 `data/{username}/memory.db` 下拥有独立的SQLite数据库，包含8张表：

| 表名 | 说明 | 关键字段 |
|------|------|----------|
| `profile` | 用户画像 | key-value键值对（角色、情绪状态等） |
| `goals` | 目标列表 | 优先级、截止日期、进度(0-100)、状态 |
| `abilities` | 技能列表 | 等级（初级/中级/高级）、类别 |
| `history` | 交互历史 | 类型、内容、元数据JSON |
| `insights` | 洞察记录 | 来源、内容、时间戳 |
| `gaps` | 能力差距 | 描述、严重程度 |
| `plans` | 成长计划 | 步骤JSON |
| `topic_entries` | 主题记忆条目 | 主题、关键词、要点 |
| `goal_dimensions` | 目标4维拆解 | 维度名、权重、得分 |
| `assessment_records` | 评估记录 | 阶段、维度得分JSON、综合得分、短板、建议 |
| `learning_sessions` | 学习会话 | 类型（learn/answer/review）、内容、AI反馈 |

## 架构说明

- 项目正处于 **v3 重构阶段** — `memory/`、`perception/`、`interaction/` 目录为旧模块的重定向桩，实际逻辑已迁移至 `mind_layer/`、`dispatch_layer/`
- `legacy/` 目录提供向后兼容的桥接类，确保平滑过渡
- 前端为零构建步骤的原生 SPA，由 FastAPI 直接托管静态文件，已拆分为 7 个 JS 模块 + 独立 CSS
- 认知管线通过 `agent.py` 中的 `UnifiedAgent` 类统一编排
- Docker 镜像已优化：合并 RUN 层、非 root 用户 (`appuser`)、HEALTHCHECK、阿里云镜像加速

## 许可证

MIT License

## 作者

[yeshanyang](https://github.com/yeshanyang)
