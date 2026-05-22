"""
SQLite 数据访问层 — 统一心智记忆的结构化持久存储
从 memory/database.py 重构，提取了 _now / _json / _keyword_score 辅助方法
"""

import sqlite3
import json
import os
from datetime import datetime


class Database:
    """SQLite 数据访问层，管理 8 张表"""

    def __init__(self, db_path: str = None):
        if db_path is None:
            base = os.path.dirname(os.path.abspath(__file__))
            db_path = os.path.join(base, "..", "memory.db")
        self.db_path = os.path.abspath(db_path)
        self._conn = None
        self._init_tables()

    # ---- 内部工具 ----

    @staticmethod
    def _now() -> str:
        return str(datetime.now())

    @staticmethod
    def _json(obj) -> str:
        return json.dumps(obj, ensure_ascii=False)

    @staticmethod
    def _keyword_score(text: str, keywords: list) -> int:
        """关键词命中得分"""
        t = (text or "").lower()
        return sum(1 for w in keywords if w in t)

    @property
    def conn(self):
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA foreign_keys=ON")
        return self._conn

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None

    def _init_tables(self):
        c = self.conn
        c.executescript("""
        CREATE TABLE IF NOT EXISTS profile (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TEXT NOT NULL DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            goal TEXT NOT NULL, priority INTEGER DEFAULT 1,
            deadline TEXT DEFAULT '', progress INTEGER DEFAULT 0,
            status TEXT DEFAULT 'active',
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS abilities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE, level TEXT DEFAULT 'beginner',
            category TEXT DEFAULT '',
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entry_type TEXT NOT NULL, content TEXT NOT NULL DEFAULT '',
            metadata_json TEXT DEFAULT '{}', created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_history_type ON history(entry_type);
        CREATE INDEX IF NOT EXISTS idx_history_created ON history(created_at);
        CREATE TABLE IF NOT EXISTS insights (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic TEXT NOT NULL DEFAULT '', insight TEXT NOT NULL,
            source TEXT DEFAULT '', created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS gaps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            area TEXT NOT NULL, current_level TEXT DEFAULT '',
            target_level TEXT DEFAULT '', severity TEXT DEFAULT 'medium',
            resolved INTEGER DEFAULT 0,
            identified_at TEXT NOT NULL, updated_at TEXT NOT NULL DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL DEFAULT '', target_gap TEXT DEFAULT '',
            steps_json TEXT DEFAULT '[]', status TEXT DEFAULT 'pending',
            created_at TEXT NOT NULL, completed_at TEXT DEFAULT NULL
        );
        CREATE TABLE IF NOT EXISTS topic_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic_slug TEXT NOT NULL, topic_name TEXT DEFAULT '',
            user_input TEXT DEFAULT '', ai_response_summary TEXT DEFAULT '',
            key_points_json TEXT DEFAULT '[]', context TEXT DEFAULT '',
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_topic_slug ON topic_entries(topic_slug);
        """)
        c.commit()

    # ==================== Profile ====================

    def get_profile(self) -> dict:
        rows = self.conn.execute("SELECT key, value FROM profile").fetchall()
        profile = {"role": "", "name": "", "current_situation": "",
                    "emotional_state": "", "updated_at": ""}
        for r in rows:
            if r["key"] in profile:
                profile[r["key"]] = r["value"]
        return profile

    def update_profile(self, **kwargs):
        now = self._now()
        for k, v in kwargs.items():
            if v:
                self.conn.execute(
                    "INSERT INTO profile(key, value, updated_at) VALUES(?, ?, ?) "
                    "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
                    (k, v, now))
        self.conn.commit()

    # ==================== Goals ====================

    def add_goal(self, goal: str, priority: int = 1, deadline: str = "") -> int:
        existing = self.conn.execute(
            "SELECT id FROM goals WHERE goal=? AND status='active'", (goal,)).fetchone()
        if existing:
            return existing["id"]
        now = self._now()
        cur = self.conn.execute(
            "INSERT INTO goals(goal, priority, deadline, progress, status, created_at, updated_at) "
            "VALUES(?,?,?,0,'active',?,?)", (goal, priority, deadline, now, now))
        self.conn.commit()
        return cur.lastrowid

    def list_goals(self, status: str = "active") -> list:
        rows = self.conn.execute(
            "SELECT * FROM goals WHERE status=? ORDER BY priority DESC, id DESC", (status,)).fetchall()
        return [dict(r) for r in rows]

    def update_goal_progress(self, goal_id: int, progress: int):
        progress = min(100, max(0, progress))
        status = "completed" if progress >= 100 else "active"
        self.conn.execute(
            "UPDATE goals SET progress=?, status=?, updated_at=? WHERE id=?",
            (progress, status, self._now(), goal_id))
        self.conn.commit()

    # ==================== Abilities ====================

    def add_ability(self, name: str, level: str = "beginner", category: str = ""):
        now = self._now()
        self.conn.execute(
            "INSERT INTO abilities(name, level, category, created_at, updated_at) "
            "VALUES(?,?,?,?,?) ON CONFLICT(name) DO UPDATE SET level=excluded.level, updated_at=excluded.updated_at",
            (name, level, category, now, now))
        self.conn.commit()

    def list_abilities(self) -> list:
        rows = self.conn.execute("SELECT * FROM abilities ORDER BY name").fetchall()
        return [dict(r) for r in rows]

    # ==================== History ====================

    def add_history(self, entry_type: str, content: str, metadata: dict = None) -> int:
        cur = self.conn.execute(
            "INSERT INTO history(entry_type, content, metadata_json, created_at) VALUES(?,?,?,?)",
            (entry_type, content, self._json(metadata or {}), self._now()))
        self.conn.commit()
        return cur.lastrowid

    def recent_history(self, n: int = 20) -> list:
        rows = self.conn.execute("SELECT * FROM history ORDER BY id DESC LIMIT ?", (n,)).fetchall()
        result = []
        for r in reversed(rows):
            d = dict(r)
            d["type"] = d.pop("entry_type", "")
            d["time"] = d.pop("created_at", "")
            d["metadata"] = json.loads(d.pop("metadata_json", "{}"))
            d.pop("id", None)
            result.append(d)
        return result

    def search_history(self, query: str, n: int = 5) -> list:
        words = query.lower().split()
        rows = self.conn.execute("SELECT * FROM history ORDER BY id DESC LIMIT 200").fetchall()
        scored = []
        for r in rows:
            score = self._keyword_score(r["content"] or "", words)
            if score > 0:
                scored.append((score, dict(r)))
        scored.sort(key=lambda x: x[0], reverse=True)
        result = []
        for s, d in scored[:n]:
            d["type"] = d.pop("entry_type", "")
            d["time"] = d.pop("created_at", "")
            d["metadata"] = json.loads(d.pop("metadata_json", "{}"))
            d.pop("id", None)
            result.append(d)
        return result

    def history_count(self) -> int:
        return self.conn.execute("SELECT COUNT(*) FROM history").fetchone()[0]

    def delete_old_history(self, keep_n: int = 20):
        if self.history_count() > keep_n:
            self.conn.execute(
                "DELETE FROM history WHERE id NOT IN (SELECT id FROM history ORDER BY id DESC LIMIT ?)",
                (keep_n,))
            self.conn.commit()

    # ==================== Insights ====================

    def add_insight(self, topic: str, insight: str, source: str = "") -> int:
        cur = self.conn.execute(
            "INSERT INTO insights(topic, insight, source, created_at) VALUES(?,?,?,?)",
            (topic, insight, source, self._now()))
        self.conn.commit()
        return cur.lastrowid

    def list_insights(self, topic: str = None) -> list:
        if topic:
            rows = self.conn.execute(
                "SELECT * FROM insights WHERE topic LIKE ? ORDER BY id DESC", (f"%{topic}%",)).fetchall()
        else:
            rows = self.conn.execute("SELECT * FROM insights ORDER BY id DESC").fetchall()
        return [dict(r) for r in rows]

    # ==================== Gaps ====================

    def add_gap(self, area: str, current_level: str, target_level: str, severity: str = "medium"):
        existing = self.conn.execute(
            "SELECT id FROM gaps WHERE area=? AND resolved=0", (area,)).fetchone()
        if existing:
            return
        now = self._now()
        self.conn.execute(
            "INSERT INTO gaps(area, current_level, target_level, severity, resolved, identified_at, updated_at) "
            "VALUES(?,?,?,?,0,?,?)", (area, current_level, target_level, severity, now, now))
        self.conn.commit()

    def list_gaps(self, resolved: bool = False) -> list:
        rows = self.conn.execute(
            "SELECT * FROM gaps WHERE resolved=? ORDER BY severity DESC, id DESC", (int(resolved),)).fetchall()
        return [dict(r) for r in rows]

    # ==================== Plans ====================

    def add_plan(self, title: str, steps: list, target_gap: str = "") -> int:
        cur = self.conn.execute(
            "INSERT INTO plans(title, target_gap, steps_json, status, created_at) VALUES(?,?,?,'pending',?)",
            (title, target_gap, self._json(steps), self._now()))
        self.conn.commit()
        return cur.lastrowid

    def list_plans(self, status: str = None) -> list:
        if status:
            rows = self.conn.execute(
                "SELECT * FROM plans WHERE status=? ORDER BY id DESC", (status,)).fetchall()
        else:
            rows = self.conn.execute("SELECT * FROM plans ORDER BY id DESC").fetchall()
        return [{**dict(r), "steps": json.loads(r["steps_json"] or "[]")} for r in rows]

    # ==================== Topic Entries ====================

    def add_topic_entry(self, topic_slug: str, topic_name: str = "",
                        user_input: str = "", ai_response_summary: str = "",
                        key_points: list = None, context: str = "") -> int:
        cur = self.conn.execute(
            "INSERT INTO topic_entries(topic_slug, topic_name, user_input, ai_response_summary, "
            "key_points_json, context, created_at) VALUES(?,?,?,?,?,?,?)",
            (topic_slug, topic_name, user_input, ai_response_summary,
             self._json(key_points or []), context, self._now()))
        self.conn.commit()
        return cur.lastrowid

    def get_topic_entries(self, topic_slug: str, limit: int = 50) -> list:
        rows = self.conn.execute(
            "SELECT * FROM topic_entries WHERE topic_slug=? ORDER BY id DESC LIMIT ?",
            (topic_slug, limit)).fetchall()
        return [{**dict(r), "key_points": json.loads(r["key_points_json"] or "[]"),
                  "timestamp": r["created_at"]} for r in reversed(rows)]

    def get_topic_entry_count(self, topic_slug: str) -> int:
        return self.conn.execute(
            "SELECT COUNT(*) FROM topic_entries WHERE topic_slug=?", (topic_slug,)).fetchone()[0]

    def delete_topic_entries(self, topic_slug: str):
        self.conn.execute("DELETE FROM topic_entries WHERE topic_slug=?", (topic_slug,))
        self.conn.commit()

    def list_all_topic_slugs(self) -> list:
        rows = self.conn.execute(
            "SELECT DISTINCT topic_slug, topic_name, COUNT(*) as cnt, MAX(created_at) as updated_at "
            "FROM topic_entries GROUP BY topic_slug ORDER BY updated_at DESC").fetchall()
        return [dict(r) for r in rows]

    def search_topic_entries(self, keywords: list, topic_slug: str = None, top_k: int = 5) -> list:
        rows = self.conn.execute("SELECT * FROM topic_entries ORDER BY id DESC LIMIT 500").fetchall()
        scored = []
        for r in rows:
            if topic_slug and r["topic_slug"] != topic_slug:
                continue
            ctx = " ".join([
                r["context"] or "", r["user_input"] or "",
                " ".join(json.loads(r["key_points_json"] or "[]"))
            ])
            score = self._keyword_score(ctx, keywords)
            if score > 0:
                scored.append((score, dict(r)))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [{**d, "key_points": json.loads(d.pop("key_points_json", "[]")),
                 "timestamp": d.pop("created_at", ""), "score": s} for s, d in scored[:top_k]]

    def get_topic_key_concepts(self, topic_slug: str, limit: int = 15) -> list:
        rows = self.conn.execute(
            "SELECT key_points_json FROM topic_entries WHERE topic_slug=?", (topic_slug,)).fetchall()
        from collections import Counter
        all_pts = []
        for r in rows:
            all_pts.extend(json.loads(r["key_points_json"] or "[]"))
        return [pt for pt, _ in Counter(all_pts).most_common(limit)]

    # ==================== 上下文聚合 ====================

    def get_all_for_context(self) -> str:
        """聚合所有结构化记忆为 LLM 上下文文本"""
        parts = []
        p = self.get_profile()
        if p.get("role") or p.get("current_situation"):
            parts.append(f"用户角色: {p['role']}, 处境: {p['current_situation']}")
        goals = self.list_goals("active")
        if goals:
            parts.append("活跃目标: " + "; ".join(g["goal"] for g in goals))
        abilities = self.list_abilities()
        if abilities:
            parts.append("能力: " + "; ".join(f"{a['name']}({a['level']})" for a in abilities))
        gaps = self.list_gaps(resolved=False)
        if gaps:
            parts.append("能力差距: " + "; ".join(
                f"{g['area']}({g['current_level']}->{g['target_level']})" for g in gaps))
        insights = self.list_insights()
        if insights:
            parts.append("经验: " + "; ".join(i["insight"] for i in insights[-5:]))
        return "\n".join(parts)
