"""
定时自主触发模块 — 周期性的自动复盘、督促和主动交互
使用 asyncio 实现轻量级任务调度
"""

import asyncio
import threading
import time
from datetime import datetime
from typing import Callable

from config import settings


class AutonomousScheduler:
    """自主定时任务调度器，定期触发复盘和主动交互"""

    def __init__(self):
        self._tasks = []
        self._running = False
        self._thread = None
        self._on_reflect = None
        self._on_nudge = None
        self._on_checkin = None
        self._last_reflect_time = None
        self._last_nudge_time = None
        self._pending_nudge = None
        self._pending_reflection = None

    def set_callbacks(self, on_reflect: Callable = None,
                      on_nudge: Callable = None,
                      on_checkin: Callable = None):
        """设置回调函数"""
        self._on_reflect = on_reflect
        self._on_nudge = on_nudge
        self._on_checkin = on_checkin

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
        """后台调度循环"""
        # 初始化时间，避免启动后立即触发
        self._last_reflect_time = datetime.now()
        self._last_nudge_time = datetime.now()

        while self._running:
            now = datetime.now()
            reflect_interval = (now - self._last_reflect_time).total_seconds() / 60
            nudge_interval = (now - self._last_nudge_time).total_seconds() / 60

            if reflect_interval >= settings.auto_reflect_interval_min:
                if self._on_reflect:
                    try:
                        result = self._on_reflect()
                        self._pending_reflection = result
                        print(f"[Scheduler] 自动复盘完成 @ {now.strftime('%H:%M')}")
                    except Exception as e:
                        print(f"[Scheduler] 复盘失败: {e}")
                self._last_reflect_time = now

            if nudge_interval >= settings.auto_nudge_interval_min:
                if self._on_nudge:
                    try:
                        result = self._on_nudge()
                        self._pending_nudge = result
                        print(f"[Scheduler] 自动督促完成 @ {now.strftime('%H:%M')}")
                    except Exception as e:
                        print(f"[Scheduler] 督促失败: {e}")
                self._last_nudge_time = now

            # 每分钟检查一次
            time.sleep(60)

    def get_pending(self) -> dict:
        """获取待推送的自动消息"""
        result = {}
        if self._pending_reflection:
            result["reflection"] = self._pending_reflection
            self._pending_reflection = None
        if self._pending_nudge:
            result["nudge"] = self._pending_nudge
            self._pending_nudge = None
        return result
