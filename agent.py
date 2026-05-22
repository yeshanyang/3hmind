"""
3hmind 自我成长智能体 — 4层架构主控制器
整合 Memory / Perception / Reasoning / Interaction 四层 + 话题记忆
"""

from config import settings
from memory.memory_layer import MemoryLayer
from memory.vector_store import VectorStore
from memory.topic_memory import TopicMemory
from perception.perception_layer import PerceptionLayer
from reasoning.reasoning_layer import ReasoningLayer
from interaction.interaction_layer import InteractionLayer


class SelfGrowthAgent:
    """3hmind 自我成长智能体 — 4层架构主控制器"""

    def __init__(self, user_id: str, data_dir: str = "data"):
        import os
        user_dir = os.path.join(data_dir, user_id)
        os.makedirs(user_dir, exist_ok=True)
        topics_dir = os.path.join(user_dir, "topics")
        os.makedirs(topics_dir, exist_ok=True)

        db_path = os.path.join(user_dir, "memory.db")
        chroma_path = os.path.join(user_dir, "chroma_db")

        self.memory = MemoryLayer(db_path)
        self.vector = VectorStore(chroma_path)
        self.topic_memory = TopicMemory(topics_dir=topics_dir, db=self.memory.db)
        self.perception = PerceptionLayer(self.memory)
        self.reasoning = ReasoningLayer(self.memory, self.perception, self.vector, self.topic_memory)
        self.interaction = InteractionLayer(self.memory, self.perception, self.reasoning)
        self._inquiry_session = None  # 追问会话状态

    # ========== Inquiry Session (追问会话) ==========

    def inquiry_start(self, topic: str = "") -> dict:
        """启动一个追问会话，生成渐进式问题链"""
        questions = self.reasoning.generate_question_chain(topic)
        self._inquiry_session = {
            "active": True,
            "topic": topic or "深度对话",
            "questions": [
                {"id": i, "text": q.get("text", str(q)), "purpose": q.get("purpose", ""),
                 "asked": False, "answer_summary": ""}
                for i, q in enumerate(questions)
            ],
            "current_index": 0,
            "context_accumulated": "",
            "insights_collected": []
        }
        return {
            "topic": self._inquiry_session["topic"],
            "total": len(questions),
            "questions": [{"id": q["id"], "text": q["text"], "purpose": q["purpose"]}
                          for q in self._inquiry_session["questions"]]
        }

    def inquiry_next(self, user_answer: str = "") -> dict:
        """处理用户对当前问题的回答，返回下一个问题或结束"""
        if not self._inquiry_session or not self._inquiry_session["active"]:
            return {"done": True, "message": "没有活跃的追问会话"}

        session = self._inquiry_session
        idx = session["current_index"]

        # 记录当前问题的回答
        if idx < len(session["questions"]) and user_answer:
            q = session["questions"][idx]
            q["asked"] = True
            q["answer_summary"] = user_answer[:300]
            session["context_accumulated"] += f"\n问: {q['text']}\n答: {user_answer[:300]}"

            # 自动提取洞察
            insight = self.reasoning.extract_insight_from_answer(
                q["text"], user_answer, session["context_accumulated"]
            )
            if insight:
                session["insights_collected"].append(insight)
                self.memory.add_insight(
                    topic=session["topic"],
                    insight=insight,
                    source="inquiry-session"
                )

            # 自动更新画像
            self._auto_update_profile(f"追问: {q['text']}\n用户: {user_answer}")

        # 前进到下一个问题
        session["current_index"] += 1

        # 检查是否结束
        if session["current_index"] >= len(session["questions"]):
            result = self._inquiry_finish()
            result["acknowledgment"] = self.reasoning.generate_transition_response(
                user_answer, "", is_final=True
            )
            return result

        # 返回下一个问题 + 简短过渡
        next_q = session["questions"][session["current_index"]]
        ack = self.reasoning.generate_transition_response(
            user_answer, next_q["text"]
        )
        return {
            "done": False,
            "index": session["current_index"],
            "total": len(session["questions"]),
            "question": next_q["text"],
            "purpose": next_q.get("purpose", ""),
            "progress": f"{session['current_index'] + 1}/{len(session['questions'])}",
            "acknowledgment": ack
        }

    def _inquiry_finish(self) -> dict:
        """结束追问会话，整合记忆"""
        session = self._inquiry_session
        insights = session.get("insights_collected", [])
        context = session.get("context_accumulated", "")

        # 生成总结
        summary = self.reasoning.summarize_inquiry(
            session["topic"], context, insights
        )

        self.memory.add_history(
            entry_type="inquiry_summary",
            content=summary,
            metadata={"topic": session["topic"], "questions": len(session["questions"])}
        )
        self.memory.add_insight(
            topic=session["topic"],
            insight=summary[:200],
            source="inquiry-complete"
        )
        self.memory.consolidate()

        session["active"] = False
        self._inquiry_session = session

        return {
            "done": True,
            "total": len(session["questions"]),
            "completed": session["current_index"],
            "insights": insights,
            "summary": summary
        }

    def inquiry_status(self) -> dict:
        """获取当前追问会话状态"""
        if not self._inquiry_session or not self._inquiry_session.get("active"):
            return {"active": False}
        s = self._inquiry_session
        return {
            "active": True,
            "topic": s["topic"],
            "current_index": s["current_index"],
            "total": len(s["questions"]),
            "questions": [
                {"id": q["id"], "text": q["text"], "asked": q["asked"],
                 "answer_summary": q["answer_summary"][:100] if q.get("answer_summary") else ""}
                for q in s["questions"]
            ],
            "insights_count": len(s["insights_collected"])
        }

    def inquiry_stop(self) -> dict:
        """手动停止追问会话"""
        if self._inquiry_session and self._inquiry_session.get("active"):
            return self._inquiry_finish()
        return {"done": True, "message": "无活跃会话"}

    def startup(self) -> str:
        greeting = self.interaction.greet_and_checkin()
        status = self.interaction.profile_status()
        if not status["complete"]:
            question = self.reasoning.generate_discovery_question()
            greeting += f"\n\n[画像探索] {question}"
        return greeting

    def _auto_update_profile(self, conversation_text: str):
        """每次对话后自动提取并更新画像信息"""
        extracted = self.reasoning.extract_profile_info(conversation_text)
        if not extracted:
            return

        # 更新 profile 字段（非空才写入）
        updates = {}
        for field in ["role", "current_situation", "emotional_state"]:
            if extracted.get(field):
                updates[field] = extracted[field]
        if updates:
            self.memory.update_profile(**updates)

        # 自动添加新发现的目标
        for goal in extracted.get("new_goals", []):
            if goal and isinstance(goal, str):
                self.memory.add_goal(goal, priority=1)

        # 自动添加新发现的能力
        for ab in extracted.get("new_abilities", []):
            if isinstance(ab, dict) and ab.get("name"):
                self.memory.add_ability(ab["name"], ab.get("level", "beginner"))

    def chat_stream(self, question: str):
        """流式聊天，用于在线语音对话模式"""
        self.memory.add_history(
            entry_type="chat",
            content=question,
            metadata={"topic": question[:30]}
        )
        full_response = ""
        for token in self.reasoning.analyze_problem_stream(question):
            full_response += token
            yield token
        # 对话完成后自动提取画像
        self._auto_update_profile(f"用户: {question}\nAI: {full_response}")

    def chat(self, question: str) -> dict:
        """主交互入口，返回结构化结果"""
        self.memory.add_history(
            entry_type="chat",
            content=question,
            metadata={"topic": question[:30]}
        )

        analysis = self.reasoning.analyze_problem(question)
        decompose = self.interaction.decompose_question(question)
        feedback = self.interaction.collect_feedback()

        # 存储到向量记忆
        self.vector.add(
            content=f"Q: {question}\nA: {analysis[:500]}",
            category="conversation",
            metadata={"question": question}
        )

        # 对话完成后自动提取画像
        self._auto_update_profile(f"用户: {question}\nAI: {analysis}")

        return {
            "analysis": analysis,
            "decompose": decompose,
            "feedback": feedback
        }

    def review(self) -> str:
        return self.reasoning.reflect()

    def plan(self, gap_area: str = None) -> str:
        return self.reasoning.generate_growth_plan(gap_area)

    def nudge(self) -> str:
        return self.interaction.nudge()

    def generate_follow_up_question(self, last_user_msg: str = "",
                                     last_ai_response: str = "") -> str:
        """生成 AI 主动追问，用于在线对话模式中 AI 驱动对话继续"""
        return self.reasoning.generate_follow_up_question(
            last_user_msg, last_ai_response
        )

    def update_profile(self, **kwargs):
        self.memory.update_profile(**kwargs)

    def add_goal(self, goal: str, priority: int = 1):
        self.memory.add_goal(goal, priority)

    def add_ability(self, name: str, level: str = "beginner"):
        self.memory.add_ability(name, level)

    def show_dashboard(self) -> str:
        situation = self.perception.assess_situation()
        goals = self.memory.list_goals("active")
        gaps = self.memory.list_gaps(resolved=False)
        insights = self.memory.list_insights()
        profile = self.memory.get_profile()

        lines = [
            "=" * 50,
            "  [3hmind 个人成长仪表盘]",
            "=" * 50,
            "",
            "[个人画像]:",
            f"  角色: {profile.get('role', '未设置')}",
            f"  当前处境: {profile.get('current_situation', '未描述')}",
            f"  情绪状态: {profile.get('emotional_state', '未记录')}",
            "",
            "[活跃目标]:",
        ]
        for g in goals:
            pct = g["progress"] // 10
            bar = "#" * pct + "-" * (10 - pct)
            lines.append(f"  [{bar}] {g['goal']} ({g['progress']}%)")
        if not goals:
            lines.append("  (无)")

        lines.extend(["", "[能力项]:"])
        for a in self.memory.list_abilities():
            lines.append(f"  - {a['name']} ({a['level']})")
        if not self.memory.list_abilities():
            lines.append("  (无)")

        lines.extend(["", "[能力差距]:"])
        for g in gaps:
            lines.append(f"  - {g['area']}: {g.get('current_level', g.get('current', ''))} -> "
                        f"{g.get('target_level', g.get('target', ''))} [{g['severity']}]")
        if not gaps:
            lines.append("  (无)")

        lines.extend(["", f"[沉淀经验]: {len(insights)}条"])

        # 话题记忆（按优先级排列）
        topics = self.list_topics()
        if topics:
            lines.extend(["", "[话题记忆库] (按重要性排列):"])
            for t in topics[:8]:
                stars = "★" * (t.get("priority", 1) // 2) + "☆" * (5 - t.get("priority", 1) // 2)
                custom = " [用户设置]" if t.get("is_custom_priority") else ""
                lines.append(f"  [{stars}] {t['name']}: {t['entries']}条 | {t.get('summary', '')[:50]}{custom}")
            if len(topics) > 8:
                lines.append(f"  ... 共{len(topics)}个话题")

        lines.append("=" * 50)
        return "\n".join(lines)

    # ========== 话题记忆 (Topic Memory) ==========

    def search_topics(self, query: str) -> list:
        """搜索相关话题记忆"""
        return self.reasoning.search_topic_memory(query)

    def list_topics(self) -> list:
        """列出所有话题"""
        return self.reasoning.get_topic_list()

    def get_topic(self, topic_slug: str) -> dict:
        """获取话题详情"""
        return self.reasoning.get_topic_detail(topic_slug)

    def set_topic_priority(self, topic_slug: str, priority: int) -> dict:
        """设置话题重要性（1-10），数值越高越重要"""
        return self.topic_memory.set_topic_priority(topic_slug, priority)

    def optimize_topic(self, topic_slug: str = None) -> dict:
        """整理优化话题记忆"""
        tm = self.topic_memory
        if topic_slug:
            return tm.optimize(topic_slug)
        # 优化所有话题
        results = {}
        for t in tm.list_all_topics():
            results[t["slug"]] = tm.optimize(t["slug"])
        return results
