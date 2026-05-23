"""
中央记忆协调器 — 统一管理所有子存储
整合 Database + VectorKB + TopicMemoryStore + SessionMemory + UserProfile
提供 get_context_for_llm() 统一入口，消除 reasoning_layer 中的重复上下文拼装
"""

from datetime import datetime
from collections import Counter

from config import settings
from mind_layer.database import Database
from mind_layer.vector_kb import VectorKB
from mind_layer.topic_memory import TopicMemoryStore
from mind_layer.session_memory import SessionMemory
from mind_layer.user_profile import UserProfile
from dispatch_layer.assessment_engine import AssessmentEngine


class MemoryOrchestrator:
    """中央记忆协调器 — 统一心智记忆层的唯一入口"""

    def __init__(self, db_path: str, chroma_path: str = None, topics_dir: str = None):
        self.db = Database(db_path)
        self.vector = VectorKB(chroma_path or db_path.replace(".db", "_chroma"))
        self.topics = TopicMemoryStore(topics_dir=topics_dir, db=self.db)
        self.session = SessionMemory()
        self.profile = UserProfile(self.db)
        self.assessment = AssessmentEngine(self.db)


    # ==================== 统一上下文（核心） ====================

    def get_context_for_llm(self, question: str) -> str:
        """一次性收集所有 LLM 所需上下文，替代 reasoning_layer 中的分散拼装"""
        parts = []

        # 结构化记忆
        structured = self.db.get_all_for_context()
        if structured:
            parts.append(structured)

        # 向量相似记忆
        similar = self._search_similar(question)
        if similar:
            parts.append(f"相关记忆:\n{similar}")

        # 话题记忆
        topic_ctx = self.topics.get_context_for_llm(question)
        if topic_ctx:
            parts.append(topic_ctx)

        # 会话上下文
        session_ctx = self.session.get_context(5)
        if session_ctx:
            parts.append(f"最近对话:\n{session_ctx}")

        return "\n\n".join(parts)

    def _search_similar(self, query: str) -> str:
        results = self.vector.search(query, top_k=3)
        if not results:
            return ""
        return "\n".join(f"- [{r['category']}] {r['content'][:200]}" for r in results)

    # ==================== 交互记录 ====================

    def record_interaction(self, question: str, response: str, topic: str = ""):
        """记录一轮完整交互到所有子存储"""
        self.db.add_history(entry_type="chat", content=question,
                            metadata={"topic": topic or question[:30]})
        self.vector.add(
            content=f"Q: {question}\nA: {response[:500]}",
            category="conversation",
            metadata={"question": question, "time": str(datetime.now())})
        self.session.add_turn(question, response, topic)

    # ==================== 跨会话同步 ====================

    def cross_session_sync(self):
        """会话结束后持久化关键信息到长期记忆"""
        distribution = self.session.topic_distribution
        if distribution:
            top_topics = sorted(distribution.items(), key=lambda x: x[1], reverse=True)[:3]
            self.db.add_insight(
                topic="会话摘要",
                insight=f"本次对话主要话题: {', '.join(f'{t}({c}次)' for t, c in top_topics)}",
                source="session-sync")
        self.session.clear()

    # ==================== 委托方法（保持与原 API 兼容） ====================

    def get_profile(self) -> dict:
        return self.profile.get()

    def update_profile(self, **kwargs):
        self.profile.update(**kwargs)

    def add_goal(self, goal: str, priority: int = 1, deadline: str = ""):
        self.db.add_goal(goal, priority, deadline)

    def list_goals(self, status: str = "active") -> list:
        return self.db.list_goals(status)

    def update_goal_progress(self, goal_id: int, progress: int):
        self.db.update_goal_progress(goal_id, progress)

    def delete_goal(self, goal_id: int):
        self.db.delete_goal(goal_id)

    def assess_goal(self, goal_id: int, phase: str = "baseline") -> dict:
        return self.assessment.assess_goal(goal_id, phase)

    def assess_with_llm(self, goal_id: int, phase: str = "baseline",
                        user_content: str = "", reasoning=None) -> dict:
        self.assessment.reasoning = reasoning
        return self.assessment.assess_with_llm(goal_id, phase, user_content)

    def start_learning_session(self, goal_id: int, content: str = "") -> dict:
        return self.assessment.start_learning_session(goal_id, content)

    def submit_learning_answer(self, goal_id: int, user_response: str) -> dict:
        return self.assessment.submit_answer(goal_id, user_response)

    def verify_goal(self, goal_id: int, user_content: str = "",
                    reasoning=None) -> dict:
        self.assessment.reasoning = reasoning
        return self.assessment.verify_goal(goal_id, user_content)

    def get_assessment_history(self, goal_id: int) -> list:
        return self.assessment.get_assessment_history(goal_id)

    def get_progress_trend(self, goal_id: int) -> dict:
        return self.assessment.get_progress_trend(goal_id)

    def add_ability(self, name: str, level: str = "beginner", category: str = ""):
        self.db.add_ability(name, level, category)

    def list_abilities(self) -> list:
        return self.db.list_abilities()

    def add_history(self, entry_type: str, content: str, metadata: dict = None) -> dict:
        self.db.add_history(entry_type, content, metadata)
        return {"time": str(datetime.now()), "type": entry_type,
                "content": content, "metadata": metadata or {}}

    def recent_history(self, n: int = 20) -> list:
        return self.db.recent_history(n)

    def search_history(self, query: str, n: int = 5) -> list:
        return self.db.search_history(query, n)

    def add_insight(self, topic: str, insight: str, source: str = ""):
        self.db.add_insight(topic, insight, source)

    def list_insights(self, topic: str = None) -> list:
        return self.db.list_insights(topic)

    def add_gap(self, area: str, current_level: str, target_level: str, severity: str = "medium"):
        self.db.add_gap(area, current_level, target_level, severity)

    def list_gaps(self, resolved: bool = False) -> list:
        return self.db.list_gaps(resolved)

    def add_plan(self, title: str, steps: list, target_gap: str = ""):
        self.db.add_plan(title, steps, target_gap)

    def list_plans(self, status: str = None) -> list:
        return self.db.list_plans(status)

    def consolidate(self):
        """记忆整合：旧历史记录提炼为 insights"""
        total = self.db.history_count()
        if total < settings.consolidate_threshold:
            return
        old = self.db.conn.execute(
            "SELECT metadata_json FROM history ORDER BY id ASC LIMIT ?",
            (total - 20,)).fetchall()
        import json
        topics = Counter()
        for r in old:
            meta = json.loads(r["metadata_json"] or "{}")
            topics[meta.get("topic", "general")] += 1
        summary = ", ".join(f"{t}(x{c})" for t, c in topics.most_common(3))
        self.db.add_insight(
            topic="记忆整合", insight=f"历史对话摘要: {summary}", source="auto-consolidate")
        self.db.delete_old_history(keep_n=20)

    def get_all_for_context(self) -> str:
        return self.db.get_all_for_context()

    # ==================== 话题记忆委托 ====================

    def search_topics(self, query: str) -> list:
        return self.topics.search(query)

    def list_topics(self) -> list:
        return self.topics.list_all_topics()

    def get_topic(self, topic_slug: str) -> dict:
        return self.topics.get_topic_for_agent(topic_slug)

    def set_topic_priority(self, topic_slug: str, priority: int) -> dict:
        return self.topics.set_topic_priority(topic_slug, priority)

    def optimize_topic(self, topic_slug: str = None) -> dict:
        if topic_slug:
            return self.topics.optimize(topic_slug)
        return {t["slug"]: self.topics.optimize(t["slug"])
                for t in self.topics.list_all_topics()}
