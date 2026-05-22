"""
3hmind 统一智能体 — 入口文件
5 层架构: 输入 → 意图 → 记忆 → 调度 → 输出
启动 Web 服务 + 自主定时调度（多用户支持）
"""

import threading

import uvicorn

from config import settings
from agent import UnifiedAgent
from scheduler import AutonomousScheduler
from auth import seed_default_admin, list_users


# [LEGACY] 历史数据迁移 — 旧版单用户数据 → admin 用户目录，已不再需要
# def migrate_legacy_data(): ...


def main():
    print("=" * 50)
    print("  3hmind - 统一智能体 v3.0")
    print("  5层架构: 输入 / 意图 / 记忆 / 调度 / 输出")
    print("  多用户支持")
    print("=" * 50)

    # [LEGACY] migrate_legacy_data() — 已注释
    seed_default_admin()

    from web.app import app

    # Agent 注册表
    app.state.agents: dict[str, UnifiedAgent] = {}

    def get_or_create_agent(user_id: str) -> UnifiedAgent:
        if user_id not in app.state.agents:
            agent = UnifiedAgent(user_id=user_id, data_dir=settings.data_dir)
            app.state.agents[user_id] = agent
            if app.state.scheduler:
                app.state.scheduler.register_user(user_id, agent)
            print(f"[Agent] 为用户 '{user_id}' 创建独立数据空间")
        return app.state.agents[user_id]

    app.state.get_agent = get_or_create_agent

    scheduler = AutonomousScheduler()
    app.state.scheduler = scheduler

    for username in list_users():
        get_or_create_agent(username)

    scheduler.start()

    # 后台预热 ChromaDB
    def warm_up_embedding():
        try:
            agent = app.state.get_agent("admin")
            agent.mind.vector.add(content="warmup", category="system", metadata={})
            print("[Warmup] ChromaDB 嵌入模型加载完成")
        except Exception as e:
            print(f"[Warmup] 预热失败（非致命）: {e}")

    threading.Thread(target=warm_up_embedding, daemon=True).start()

    proto = "http"
    url = f"{proto}://localhost:{settings.port}" if settings.host == "0.0.0.0" else f"{proto}://{settings.host}:{settings.port}"
    print(f"\n[Web] 服务已启动 -> {url}")
    uvicorn.run("web.app:app", host=settings.host, port=settings.port, log_level="info")


if __name__ == "__main__":
    main()
