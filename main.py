"""
3hmind 自我成长智能体 — 入口文件
启动 Web 服务 + 自主定时调度（多用户支持）
"""

import os
import shutil
import sys
import pathlib
import threading

import uvicorn

from config import settings
from agent import SelfGrowthAgent
from scheduler import AutonomousScheduler
from auth import seed_default_admin, list_users


def migrate_legacy_data():
    """迁移旧版单用户数据到 admin 用户目录"""
    legacy_db = pathlib.Path("memory.db")
    legacy_chroma = pathlib.Path("chroma_db")
    legacy_topics = pathlib.Path("memory/topics")

    admin_dir = pathlib.Path(settings.data_dir) / "admin"
    admin_db = admin_dir / "memory.db"
    admin_chroma = admin_dir / "chroma_db"
    admin_topics = admin_dir / "topics"

    if not legacy_db.exists():
        return

    if admin_db.exists():
        return

    print("\n[Migrate] 检测到旧版单用户数据，正在迁移到 admin 用户...")
    admin_dir.mkdir(parents=True, exist_ok=True)
    admin_topics.mkdir(parents=True, exist_ok=True)

    shutil.move(str(legacy_db), str(admin_db))
    # 同时迁移 WAL 和 SHM 文件
    for suffix in [".db-wal", ".db-shm"]:
        legacy_suf = pathlib.Path("memory" + suffix)
        if legacy_suf.exists():
            shutil.move(str(legacy_suf), str(admin_dir / ("memory" + suffix)))

    if legacy_chroma.exists():
        shutil.move(str(legacy_chroma), str(admin_chroma))

    if legacy_topics.exists():
        for f in legacy_topics.glob("*.json"):
            shutil.move(str(f), str(admin_topics / f.name))

    print("[Migrate] 数据迁移完成 → data/admin/")


def main():
    print("=" * 50)
    print("  3hmind - 自我成长智能体 v2.0")
    print("  4层架构: Memory / Perception / Reasoning / Interaction")
    print("  多用户支持")
    print("=" * 50)

    # 迁移旧数据
    migrate_legacy_data()

    # 创建默认管理员
    seed_default_admin()

    # 导入 FastAPI app
    from web.app import app

    # Agent 注册表
    app.state.agents: dict[str, SelfGrowthAgent] = {}

    def get_or_create_agent(user_id: str) -> SelfGrowthAgent:
        if user_id not in app.state.agents:
            agent = SelfGrowthAgent(user_id=user_id, data_dir=settings.data_dir)
            app.state.agents[user_id] = agent
            # 注册到 scheduler
            if app.state.scheduler:
                app.state.scheduler.register_user(user_id, agent)
            print(f"[Agent] 为用户 '{user_id}' 创建独立数据空间")
        return app.state.agents[user_id]

    app.state.get_agent = get_or_create_agent

    # 初始化调度器
    scheduler = AutonomousScheduler()
    app.state.scheduler = scheduler

    # 为已有用户预建 agent（让 scheduler 在无人登录时也能触发自主任务）
    for username in list_users():
        get_or_create_agent(username)

    scheduler.start()

    # 后台预热 ChromaDB 嵌入模型（避免首次请求阻塞）
    def warm_up_embedding():
        try:
            agent = app.state.get_agent("admin")
            agent.vector.add(content="warmup", category="system", metadata={})
            print("[Warmup] ChromaDB 嵌入模型加载完成")
        except Exception as e:
            print(f"[Warmup] 预热失败（非致命）: {e}")

    threading.Thread(target=warm_up_embedding, daemon=True).start()

    # 启动 Web 服务（HTTP 模式，由 Caddy 反向代理提供 HTTPS）
    proto = "http"
    url = f"{proto}://localhost:{settings.port}" if settings.host == "0.0.0.0" else f"{proto}://{settings.host}:{settings.port}"
    print(f"\n[Web] 服务已启动 -> {url}")
    uvicorn.run(
        "web.app:app",
        host=settings.host,
        port=settings.port,
        log_level="info"
    )


if __name__ == "__main__":
    main()
