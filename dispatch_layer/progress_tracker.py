"""
进度追踪器 — 目标进度监控 + 过期提醒 + 下一步建议
"""

from datetime import datetime


class ProgressTracker:
    """监控目标进度，对停滞目标触发干预"""

    def __init__(self, mind=None):
        self.mind = mind

    def check_goals(self) -> list[dict]:
        """扫描所有活跃目标，标记进度异常"""
        goals = self.mind.list_goals("active") if self.mind else []
        flagged = []
        for g in goals:
            try:
                created = datetime.fromisoformat(g["created_at"])
                days = (datetime.now() - created).days
            except (ValueError, KeyError):
                days = 0

            if days > 7 and g["progress"] < 30:
                flagged.append({
                    "id": g["id"], "goal": g["goal"],
                    "progress": g["progress"], "days_since_created": days,
                    "status": "stale",
                    "suggestion": self._suggest_action(g),
                })
            elif g["progress"] >= 80:
                flagged.append({
                    "id": g["id"], "goal": g["goal"],
                    "progress": g["progress"], "days_since_created": days,
                    "status": "near_complete",
                })
        return flagged

    def _suggest_action(self, goal: dict) -> str:
        g = goal["goal"]
        return (
            f"你的目标「{g}」已设定一段时间了但进展不多。"
            f"建议今天花 10 分钟思考：为什么推进困难？最小可执行的下一步是什么？"
        )

    def generate_status_report(self) -> str:
        goals = self.mind.list_goals("active") if self.mind else []
        gaps = self.mind.list_gaps(resolved=False) if self.mind else []

        parts = ["【进度追踪报告】", ""]
        if goals:
            parts.append("活跃目标:")
            for g in goals:
                bar = "#" * (g["progress"] // 10) + "-" * (10 - g["progress"] // 10)
                parts.append(f"  [{bar}] {g['goal']} ({g['progress']}%)")
        else:
            parts.append("暂无活跃目标")

        if gaps:
            parts.extend(["", "待解决差距:"])
            for g in gaps:
                parts.append(f"  - {g['area']}: {g.get('current_level', '?')} → {g.get('target_level', '?')}")

        return "\n".join(parts)
