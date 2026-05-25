
import threading  # python自带后台线程，用于 ChromaDB 预热等非阻塞任务

# FastAPI BackgroundTasks（最推荐，超级简单，非阻塞，适合服务启动时做初始化、预热、缓存）
# concurrent.futures.ThreadPoolExecutor（ 线程池 / 进程池，比原生 threading 好用 10 倍.自动管理线程/不用手动写 thread.start/适合：绝大多数后台任务（ChromaDB 预热、文件加载、API 调用、DB 操作））
# threading（简单,适合：IO 密集型（等待数据库、文件、网络）缺点：有 GIL，CPU 密集型不提速；手动管理线程麻烦）
# asyncio + run_in_executor（专业级，不阻塞事件循环,异步非阻塞（高性能，适合服务端）完全非阻塞、超高并发.适合：API、长连接、批量 IO.不能直接调用阻塞函数（如 ChromaDB 加载），否则会卡住整个服务）
# multiprocessing（太重，适合：CPU 密集型（向量计算、模型推理、数据处理，heavy 计算后台任务）优点：绕过 GIL，真正并行。缺点：开销比线程大，不能共享内存）
# celery（大材小用，分布式任务队列）适合：长时间任务、定时任务、跨服务任务，太重，不适合本地 ChromaDB 预热）
# anyio（现代异步库）兼容 asyncio、trio。FastAPI 底层就是用它，更稳定、更安全。
# apscheduler（定时后台任务）定时执行、周期执行，例如：每天更新向量库
# starlette.background高性能生产级后台方案（服务专用）FastAPI 底层的后台任务，非常轻量。
# trio & nursery 更安全的异步模型，自动管理任务生命周期，不会漏后台任务。



import uvicorn  # ASGI 服务器，运行 FastAPI 应用
#ASGI（Asynchronous Server Gateway Interface） 是 Python 生态里的异步服务器网关接口，可以理解为 WSGI 的异步超集，解决 WSGI 只能同步、不支持长连接的问题ASGI。
#WSGI：只支持 HTTP/1.x、同步，一个请求占一个线程 / 进程，不支持 WebSocket / 长轮询。
#ASGI： 异步非阻塞 + 多协议 + 高并发；原生支持 HTTP/1.1、HTTP/2、WebSocket、SSE；兼容 WSGI 应用。是现在 FastAPI/Starlette/Django Channels 的标准接口。

#Uvicorn：性能最好、生态最成熟，主打 “极速 + 轻量”。底层：基于 uvloop（libuv 事件循环，比 asyncio 快 2–4 倍）+ httptools（C 语言 HTTP 解析）。协议：支持 HTTP/1.1、WebSocket（暂不支持 HTTP/2）。生产常搭配 Gunicorn 做进程管理 + Nginx 做反向代理。
#Daphne:基于 Twisted；完整支持 HTTP/1.1、HTTP/2、WebSocket/实时；Django 生态首选
#Hypercorn:全功能 ASGI 服务器，支持 asyncio / trio 两种异步模型。	特点：sans-io 设计；HTTP/1.1、HTTP/2、WebSocket 全支持；配置灵活。
#Granian:Rust 编写的高性能 ASGI 服务器，极致性能与安全。特点：支持 ASGI/WSGI/RSGI；低内存、高并发；适合生产环境。
#NGINX Unit：NGINX 出品的多语言应用服务器，原生支持 ASGI。特点：动态配置、热重载；支持 HTTP/1.1、WebSocket；可跑 Python/PHP/Go 等。
#Mangum：AWS Lambda 专用 ASGI 适配器，用于把 ASGI 应用部署到 Lambda。

from config import settings  # 全局配置对象（从 .env 读取）
from agent import UnifiedAgent  # agent智能体框架。五层认知管线协调器
###极简自研型智能体
#UnifiedAgent = 自研轻量智能体（认知管线 + 记忆 + 规划 + 执行 + 工具调用 + RAG）
#agentle超轻量无依赖=感知 → 理解 → 行动 → 记忆
#simple-agent几十行代码实现一个智能体，适合理解底层原理
#
### 企业级认知智能体（带真正 “五层思考管线”）
#LangChain = 通用强大版（最主流、最通用一站式大模型智能体框架，工具多、文档全、适合复杂任务、企业最常用）=感知 → 理解 → 记忆 → 规划 → 执行。包括Agent（智能体）Tools（工具调用）RAG（Chroma/FAISS 检索）Memory（记忆）Chain / Pipeline（管线编排）适合：快速搭建类人思考 AI
#LlamaIndex（RAG 优先的智能体，和 Chroma 天生适配）定位：专门做知识库 + 智能体、特点：比 LangChain 更专注检索、思考、决策。最适合你的场景：文档问答 + 思考规划。对应：你的五层认知 + ChromaDB 记忆
#Transformers Agent（Hugging Face 官方智能体）超轻量、支持工具调用、支持多模态、适合小模型做智能体
#AutoGPT 框架：agpt、真正的自主智能体会自己规划、反思、查资料、执行、对应五层认知、开源、Python 直接运行
#BabyAGI：经典任务拆解智能体=感知 → 目标 → 规划 → 执行 → 存储记忆
#TaskWeaver（微软开源企业级认知智能体）代码生成 + 工具调用 + 规划
#
####多智能体（多个大脑协同）
#AutoGen（微软）多个 AI 互相聊天完成任务可做复杂工作流工业级稳定
#LangGraph（LangChain 官方）专门做认知管线、状态机、思考循环最接近你 “五层认知管线协调器” 的设计思想
#CrewAI多角色智能体（产品、程序员、分析师）目前最火

from scheduler import AutonomousScheduler  # 后台定时任务调度器（反思 / 轻推）
#AutonomousScheduler = 自主定时后台调度（反思 / 轻推）
#最佳替代：APScheduler（最稳定、最通用）
#最简单：asyncio 后台任务
#AI 原生：LangGraph 后台循环

from auth import seed_default_admin, list_users  # 首次启动创建默认管理员、列出所有用户


def main():
    # 如果 .env 中配置了默认管理员密码，则首次启动时自动创建 admin 用户
    seed_default_admin()

    # 延迟导入避免循环依赖（web.app 会 import agent 等模块）
    from web.app import app

    # 用户级 Agent 注册表，key=用户名，value=该用户的 UnifiedAgent 实例
    app.state.agents: dict[str, UnifiedAgent] = {}  # type: ignore[valid-type]

    def get_or_create_agent(user_id: str) -> UnifiedAgent:
        """按需创建或获取用户专属 Agent（每个用户独立 SQLite + ChromaDB）"""
        if user_id not in app.state.agents:
            # 创建该用户的 Agent 实例，data_dir 下会有独立子目录
            agent = UnifiedAgent(user_id=user_id, data_dir=settings.data_dir)
            app.state.agents[user_id] = agent
            # 注册到调度器，让该用户也参与后台定时反思 / 轻推
            if app.state.scheduler:
                app.state.scheduler.register_user(user_id, agent)
            print(f"[Agent] 为用户 '{user_id}' 创建独立数据空间")
        return app.state.agents[user_id]

    # 将工厂函数挂载到 app.state，路由中通过 app.state.get_agent(user) 调用
    app.state.get_agent = get_or_create_agent

    # 初始化全局自动调度器
    scheduler = AutonomousScheduler()
    app.state.scheduler = scheduler  # 暴露给路由和后台使用

    # 为所有已有用户预热 Agent 实例
    for username in list_users():
        get_or_create_agent(username)

    # 启动后台调度线程（定时反思 + 轻推）
    scheduler.start()

    # 后台预热 ChromaDB 嵌入模型（首次调用时 ChromaDB 会下载 ONNX 模型，耗时较长）用户提问 → 转向量 → 在 ChromaDB 比对向量距离 → 取出相似文档 → 喂给 LLM 回答。作用：实现知识库问答、文档检索、内容匹配。
    def warm_up_embedding():
        try:
            agent = app.state.get_agent("admin")
            # 写入一条临时记录触发嵌入模型加载，完成后 ChromaDB 后续调用不再等待
            agent.mind.vector.add(content="warmup", category="system", metadata={})
            print("[Warmup] ChromaDB 嵌入模型加载完成")
        except Exception as e:
            print(f"[Warmup] 预热失败（非致命）: {e}")

    threading.Thread(target=warm_up_embedding, daemon=True).start()  # daemon=True 保证主进程退出时自动结束

    # 打印启动信息
    proto = "http"
    url = f"{proto}://localhost:{settings.port}" if settings.host == "0.0.0.0" else f"{proto}://{settings.host}:{settings.port}"
    print(f"\n[Web] 服务已启动 -> {url}")
    # 启动 Uvicorn ASGI 服务器，阻塞主线程直到进程被终止
    uvicorn.run("web.app:app", host=settings.host, port=settings.port, log_level="info")


if __name__ == "__main__":
    main()
