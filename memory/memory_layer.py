"""
Layer 1: 长期记忆层 — SQLite 结构化存储 + 向量语义检索
"""

from datetime import datetime
from collections import Counter
from typing import Optional

from config import settings
from memory.database import Database


class MemoryLayer:
    """负责所有持久化数据的读写、整合与检索（SQLite 后端）"""

    def __init__(self, filepath: str = None):
        db_path = filepath or settings.memory_path
        # 如果传入的是旧的 JSON 路径，替换为 .db 后缀
        if db_path.endswith(".json"):
            db_path = db_path[:-5] + ".db"
        self.db = Database(db_path)
        self._migrate_if_empty()

    def _migrate_if_empty(self):
        """如果数据库为空，尝试从旧的 JSON 文件迁移"""
        import json
        if self.db.history_count() > 0:
            return  # 已有数据，不需要迁移

        # 检查 JSON 文件是否存在并有数据
        json_path = self.db.db_path.replace(".db", ".json")
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if data.get("history") or data.get("goals"):
                self._import_json_data(data)
                print(f"[Migration] 从 {json_path} 迁移了 "
                      f"{len(data.get('goals', []))}个目标, "
                      f"{len(data.get('history', []))}条历史")
        except (FileNotFoundError, json.JSONDecodeError):
            pass

    def _import_json_data(self, data: dict):
        """从旧 JSON 格式导入数据"""
        p = data.get("profile", {})
        if p.get("role"):
            self.db.update_profile(role=p["role"])
        if p.get("current_situation"):
            self.db.update_profile(current_situation=p["current_situation"])
        if p.get("emotional_state"):
            self.db.update_profile(emotional_state=p["emotional_state"])

        for g in data.get("goals", []):
            self.db.add_goal(g.get("goal", ""), g.get("priority", 1))

        for a in data.get("abilities", []):
            self.db.add_ability(a.get("name", ""), a.get("level", "beginner"))

        for h in data.get("history", []):
            self.db.add_history(
                h.get("type", h.get("entry_type", "chat")),
                h.get("content", ""),
                h.get("metadata", {})
            )

        for i in data.get("insights", []):
            self.db.add_insight(
                i.get("topic", ""), i.get("insight", ""), i.get("source", "")
            )

        for g in data.get("gaps", []):
            self.db.add_gap(
                g.get("area", ""), g.get("current", ""), g.get("target", ""),
                g.get("severity", "medium")
            )

        for p in data.get("plans", []):
            self.db.add_plan(
                p.get("title", ""), p.get("steps", []), p.get("target_gap", "")
            )

    def save(self):
        """SQLite 自动持久化，保留此方法用于 API 兼容"""
        pass

    # ========== Profile ==========

    def get_profile(self) -> dict:
        return self.db.get_profile()

    def update_profile(self, **kwargs):
        self.db.update_profile(**kwargs)

    # ========== Goals ==========

    def add_goal(self, goal: str, priority: int = 1, deadline: str = ""):
        self.db.add_goal(goal, priority, deadline)

    def list_goals(self, status: str = "active") -> list:
        return self.db.list_goals(status)

    def update_goal_progress(self, goal_id: int, progress: int):
        self.db.update_goal_progress(goal_id, progress)

    # ========== Abilities ==========

    def add_ability(self, name: str, level: str = "beginner", category: str = ""):
        self.db.add_ability(name, level, category)

    def list_abilities(self) -> list:
        return self.db.list_abilities()

    # ========== History ==========

    def add_history(self, entry_type: str, content: str, metadata: dict = None) -> dict:
        self.db.add_history(entry_type, content, metadata)
        return {"time": str(datetime.now()), "type": entry_type,
                "content": content, "metadata": metadata or {}}

    def recent_history(self, n: int = 20) -> list:
        return self.db.recent_history(n)

    def search_history(self, query: str, n: int = 5) -> list:
        return self.db.search_history(query, n)

    # ========== Insights ==========

    def add_insight(self, topic: str, insight: str, source: str = ""):
        self.db.add_insight(topic, insight, source)

    def list_insights(self, topic: str = None) -> list:
        return self.db.list_insights(topic)

    # ========== Gaps ==========

    def add_gap(self, area: str, current_level: str, target_level: str,
                severity: str = "medium"):
        self.db.add_gap(area, current_level, target_level, severity)

    def list_gaps(self, resolved: bool = False) -> list:
        return self.db.list_gaps(resolved)

    # ========== Plans ==========

    def add_plan(self, title: str, steps: list, target_gap: str = ""):
        self.db.add_plan(title, steps, target_gap)

    def list_plans(self, status: str = None) -> list:
        return self.db.list_plans(status)

    # ========== Consolidation ==========

    def consolidate(self):
        """将旧的历史记录提炼为 insights，防止记忆膨胀"""
        total = self.db.history_count()
        if total < settings.consolidate_threshold:
            return
        # 获取旧记录的主题统计
        old = self.db.conn.execute(
            "SELECT metadata_json FROM history ORDER BY id ASC LIMIT ?",
            (total - 20,)
        ).fetchall()
        import json
        topics = Counter()
        for r in old:
            meta = json.loads(r["metadata_json"] or "{}")
            topics[meta.get("topic", "general")] += 1
        summary_parts = [f"{t}(x{c})" for t, c in topics.most_common(3)]
        self.db.add_insight(
            topic="记忆整合",
            insight=f"历史对话摘要: {', '.join(summary_parts)}",
            source="auto-consolidate"
        )
        self.db.delete_old_history(keep_n=20)

    def get_all_for_context(self) -> str:
        return self.db.get_all_for_context()
