"""
3hmind 自我成长智能体 — 入口文件
启动 Web 服务 + 自主定时调度
"""

import sys
import uvicorn

from config import settings
from agent import SelfGrowthAgent
from scheduler import AutonomousScheduler


def main():
    print("=" * 50)
    print("  3hmind - 自我成长智能体 v2.0")
    print("  4层架构: Memory / Perception / Reasoning / Interaction")
    print("=" * 50)

    # 初始化 agent
    print("\n[Init] 初始化智能体...")
    agent = SelfGrowthAgent(
        memory_path=settings.memory_path,
        vector_path=settings.vector_path
    )
    print(agent.startup())

    # 初始化自主调度器
    scheduler = AutonomousScheduler()
    scheduler.set_callbacks(
        on_reflect=agent.review,
        on_nudge=agent.nudge,
        on_checkin=agent.startup
    )
    scheduler.start()

    # 注入到 FastAPI app state
    from web.app import app
    app.state.agent = agent
    app.state.scheduler = scheduler

    # 启动 Web 服务
    url = f"http://localhost:{settings.port}" if settings.host == "0.0.0.0" else f"http://{settings.host}:{settings.port}"
    print(f"\n[Web] 服务已启动 -> {url} (浏览器打开此地址)")
    uvicorn.run(
        "web.app:app",
        host=settings.host,
        port=settings.port,
        log_level="info"
    )


if __name__ == "__main__":
    main()
