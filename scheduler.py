"""
定时自主触发模块 — 周期性的自动复盘、督促和主动交互
支持多用户：每个用户独立计时，独立触发
"""

import threading
import time
from datetime import datetime

from config import settings


class AutonomousScheduler:
    """自主定时任务调度器，支持多用户"""

    def __init__(self):
        self._agents: dict[str, object] = {}  # user_id -> agent
        self._running = False
        self._thread = None
        self._last_reflect: dict[str, datetime] = {}
        self._last_nudge: dict[str, datetime] = {}
        self._pending: dict[str, dict] = {}

    def register_user(self, user_id: str, agent: object):
        """注册用户 agent，后续自动触发"""
        self._agents[user_id] = agent
        now = datetime.now()
        self._last_reflect[user_id] = now
        self._last_nudge[user_id] = now

    def start(self):
        """启动后台调度线程"""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        print(f"[Scheduler] 自主触发已启动 "
              f"(复盘每{settings.auto_reflect_interval_min}分钟, "
              f"督促每{settings.auto_nudge_interval_min}分钟)")

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)

    def _loop(self):
        """后台调度循环 — 遍历所有注册用户"""
        while self._running:
            now = datetime.now()

            for user_id, agent in self._agents.items():
                if user_id not in self._last_reflect:
                    self._last_reflect[user_id] = now
                if user_id not in self._last_nudge:
                    self._last_nudge[user_id] = now

                reflect_interval = (now - self._last_reflect[user_id]).total_seconds() / 60
                nudge_interval = (now - self._last_nudge[user_id]).total_seconds() / 60

                if reflect_interval >= settings.auto_reflect_interval_min:
                    try:
                        result = agent.review()
                        if user_id not in self._pending:
                            self._pending[user_id] = {}
                        self._pending[user_id]["reflection"] = result
                        print(f"[Scheduler] 自动复盘完成 @ {now.strftime('%H:%M')} (user={user_id})")
                    except Exception as e:
                        print(f"[Scheduler] 复盘失败 (user={user_id}): {e}")
                    self._last_reflect[user_id] = now

                if nudge_interval >= settings.auto_nudge_interval_min:
                    try:
                        result = agent.nudge()
                        if user_id not in self._pending:
                            self._pending[user_id] = {}
                        self._pending[user_id]["nudge"] = result
                        print(f"[Scheduler] 自动督促完成 @ {now.strftime('%H:%M')} (user={user_id})")
                    except Exception as e:
                        print(f"[Scheduler] 督促失败 (user={user_id}): {e}")
                    self._last_nudge[user_id] = now

            time.sleep(60)

    def get_pending(self, user_id: str) -> dict:
        """获取并清除指定用户的待推送消息"""
        result = self._pending.pop(user_id, {})
        return result

    def remove_user(self, user_id: str):
        """移除用户（清理定时器状态）"""
        self._agents.pop(user_id, None)
        self._last_reflect.pop(user_id, None)
        self._last_nudge.pop(user_id, None)
        self._pending.pop(user_id, None)
