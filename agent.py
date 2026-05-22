"""
3hmind 统一智能体 — 5 层架构主控制器
Layer 1: 多模态输入 → Layer 2: 深层意图解析 → Layer 3: 统一心智记忆 → Layer 4: 任务调度执行 → Layer 5: 多模态输出
"""

import os

from config import settings
from mind_layer.memory_orchestrator import MemoryOrchestrator
from intent_layer.intent_parser import IntentParser
from input_layer.input_parser import UnifiedInputParser
from input_layer.document_processor import DocumentProcessor
from dispatch_layer.dispatcher import TaskDispatcher
from dispatch_layer.thinking_guide import ThinkingGuide
from dispatch_layer.progress_tracker import ProgressTracker
from output_layer.output_adapter import OutputAdapter
from output_layer.response_builder import ResponseBuilder
from reasoning.reasoning_layer import ReasoningLayer


class UnifiedAgent:
    """3hmind 统一智能体 — 5 层架构"""

    def __init__(self, user_id: str, data_dir: str = "data"):
        user_dir = os.path.join(data_dir, user_id)
        os.makedirs(user_dir, exist_ok=True)
        topics_dir = os.path.join(user_dir, "topics")
        os.makedirs(topics_dir, exist_ok=True)

        db_path = os.path.join(user_dir, "memory.db")
        chroma_path = os.path.join(user_dir, "chroma_db")

        # ---- Layer 3: 统一心智记忆 ----
        self.mind = MemoryOrchestrator(db_path, chroma_path, topics_dir)

        # ---- Layer 2: 深层意图解析 ----
        self.intent_parser = IntentParser()

        # ---- Layer 1: 多模态输入 ----
        self.input_parser = UnifiedInputParser(self.intent_parser)
        self.doc_processor = DocumentProcessor(self.mind)

        # ---- Layer 4: 任务调度执行 ----
        self.thinking_guide = ThinkingGuide(self.mind)
        self.progress_tracker = ProgressTracker(self.mind)
        self.dispatcher = TaskDispatcher(self.mind)

        # ---- Layer 5: 多模态输出 ----
        self.output_adapter = OutputAdapter()
        self.response_builder = ResponseBuilder()

        # ---- 临时兼容: perception/interaction 委托到新层 ----
        self.perception = _PerceptionCompat(self.mind, self.intent_parser)
        self.interaction = _InteractionCompat(self.mind, self.thinking_guide, self.progress_tracker)

        # ---- LLM 引擎 (保留 reasoning_layer 作为 LLM 后端) ----
        self.reasoning = ReasoningLayer(self.mind, self.perception, self.mind.vector, self.mind.topics)

        # ---- 追问会话 ----
        self._inquiry_session = None

    # ==================== 统一处理管线 (核心) ====================

    def process(self, text: str, context_type: str = "text", context_summary: str = "") -> dict:
        """主统一处理管线: 输入 → 意图 → 记忆 → 调度 → 输出"""
        # 1. 标准化输入
        uinput = self.input_parser.parse(text, context_type, context_summary)

        # 2. 深层意图解析
        profile_context = self.mind.get_context_for_llm(text)
        intent = self.intent_parser.parse(uinput.preprocessed_text, profile_context)

        # 3. 检索相关记忆
        memory_context = self.mind.get_context_for_llm(text)

        # 4. LLM 分析
        analysis = self.reasoning.analyze_problem(uinput.preprocessed_text)

        # 5. 工具调度
        dispatch_results = self.dispatcher.execute(intent, self.thinking_guide, self.progress_tracker)

        # 6. 构建响应
        response = self.response_builder.build(analysis, intent, dispatch_results, memory_context)

        # 7. 自适应输出
        adapted = self.output_adapter.adapt(response, context_type)

        # 8. 记录交互
        self.mind.record_interaction(text, analysis, intent.domain)

        return adapted

    # ==================== 旧 API 兼容 ====================

    def chat(self, question: str) -> dict:
        """主交互入口 — 兼容旧 API"""
        return self.process(question, "text")

    def chat_stream(self, question: str):
        """流式聊天 — 兼容旧 API"""
        self.mind.add_history(entry_type="chat", content=question,
                              metadata={"topic": question[:30]})
        full_response = ""
        for token in self.reasoning.analyze_problem_stream(question):
            full_response += token
            yield token
        self._auto_update_profile(f"用户: {question}\nAI: {full_response}")

    def review(self) -> str:
        return self.reasoning.reflect()

    def plan(self, gap_area: str = None) -> str:
        return self.reasoning.generate_growth_plan(gap_area)

    def nudge(self) -> str:
        return self.interaction.nudge()

    def update_profile(self, **kwargs):
        self.mind.update_profile(**kwargs)

    def add_goal(self, goal: str, priority: int = 1):
        self.mind.add_goal(goal, priority)

    def add_ability(self, name: str, level: str = "beginner"):
        self.mind.add_ability(name, level)

    def show_dashboard(self) -> str:
        return self._build_dashboard()

    # ==================== 新能力 ====================

    def think_deeper(self, topic: str) -> dict:
        """思维引导入口 — 思路拆解"""
        return self.thinking_guide.decompose_thought(topic)

    def analyze_pros_cons(self, option: str) -> dict:
        """决策辅助 — 利弊分析"""
        return self.thinking_guide.analyze_pros_cons(option)

    def track_all_goals(self) -> dict:
        """进度追踪 — 全部目标状态"""
        return {"goals": self.progress_tracker.check_goals(),
                "report": self.progress_tracker.generate_status_report()}

    def get_cognitive_state(self) -> dict:
        """跨会话认知状态同步"""
        self.mind.cross_session_sync()
        return {
            "profile_complete": self.mind.profile.is_complete(),
            "active_goals": len(self.mind.list_goals("active")),
            "unresolved_gaps": len(self.mind.list_gaps(resolved=False)),
            "total_insights": len(self.mind.list_insights()),
        }

    def generate_follow_up_question(self, last_user_msg: str = "", last_ai_response: str = "") -> str:
        return self.reasoning.generate_follow_up_question(last_user_msg, last_ai_response)

    # ==================== 追问会话 ====================

    def inquiry_start(self, topic: str = "") -> dict:
        questions = self.reasoning.generate_question_chain(topic)
        self._inquiry_session = {
            "active": True,
            "topic": topic or "深度对话",
            "questions": [{"id": i, "text": q.get("text", str(q)),
                           "purpose": q.get("purpose", ""), "asked": False, "answer_summary": ""}
                          for i, q in enumerate(questions)],
            "current_index": 0,
            "context_accumulated": "",
            "insights_collected": []}
        return {
            "topic": self._inquiry_session["topic"],
            "total": len(questions),
            "questions": [{"id": q["id"], "text": q["text"], "purpose": q["purpose"]}
                          for q in self._inquiry_session["questions"]],
        }

    def inquiry_next(self, user_answer: str = "") -> dict:
        if not self._inquiry_session or not self._inquiry_session["active"]:
            return {"done": True, "message": "没有活跃的追问会话"}

        session = self._inquiry_session
        idx = session["current_index"]

        if idx < len(session["questions"]) and user_answer:
            q = session["questions"][idx]
            q["asked"] = True
            q["answer_summary"] = user_answer[:300]
            session["context_accumulated"] += f"\n问: {q['text']}\n答: {user_answer[:300]}"

            insight = self.reasoning.extract_insight_from_answer(
                q["text"], user_answer, session["context_accumulated"])
            if insight:
                session["insights_collected"].append(insight)
                self.mind.add_insight(topic=session["topic"], insight=insight, source="inquiry-session")
            self._auto_update_profile(f"追问: {q['text']}\n用户: {user_answer}")

        session["current_index"] += 1

        if session["current_index"] >= len(session["questions"]):
            result = self._inquiry_finish()
            result["acknowledgment"] = self.reasoning.generate_transition_response(
                user_answer, "", is_final=True)
            return result

        next_q = session["questions"][session["current_index"]]
        ack = self.reasoning.generate_transition_response(user_answer, next_q["text"])
        return {
            "done": False, "index": session["current_index"],
            "total": len(session["questions"]), "question": next_q["text"],
            "purpose": next_q.get("purpose", ""),
            "progress": f"{session['current_index'] + 1}/{len(session['questions'])}",
            "acknowledgment": ack,
        }

    def _inquiry_finish(self) -> dict:
        session = self._inquiry_session
        insights = session.get("insights_collected", [])
        context = session.get("context_accumulated", "")
        summary = self.reasoning.summarize_inquiry(session["topic"], context, insights)

        self.mind.add_history(entry_type="inquiry_summary", content=summary,
                              metadata={"topic": session["topic"], "questions": len(session["questions"])})
        self.mind.add_insight(topic=session["topic"], insight=summary[:200], source="inquiry-complete")
        self.mind.consolidate()

        session["active"] = False
        self._inquiry_session = session
        return {"done": True, "total": len(session["questions"]),
                "completed": session["current_index"], "insights": insights, "summary": summary}

    def inquiry_status(self) -> dict:
        if not self._inquiry_session or not self._inquiry_session.get("active"):
            return {"active": False}
        s = self._inquiry_session
        return {
            "active": True, "topic": s["topic"],
            "current_index": s["current_index"], "total": len(s["questions"]),
            "questions": [{"id": q["id"], "text": q["text"], "asked": q["asked"],
                           "answer_summary": q.get("answer_summary", "")[:100]}
                          for q in s["questions"]],
            "insights_count": len(s["insights_collected"]),
        }

    def inquiry_stop(self) -> dict:
        if self._inquiry_session and self._inquiry_session.get("active"):
            return self._inquiry_finish()
        return {"done": True, "message": "无活跃会话"}

    # ==================== 话题记忆 ====================

    def search_topics(self, query: str) -> list:
        return self.mind.search_topics(query)

    def list_topics(self) -> list:
        return self.mind.list_topics()

    def get_topic(self, topic_slug: str) -> dict:
        return self.mind.get_topic(topic_slug)

    def set_topic_priority(self, topic_slug: str, priority: int) -> dict:
        return self.mind.set_topic_priority(topic_slug, priority)

    def optimize_topic(self, topic_slug: str = None) -> dict:
        return self.mind.optimize_topic(topic_slug)

    # ==================== 内部辅助 ====================

    def _auto_update_profile(self, conversation_text: str):
        extracted = self.reasoning.extract_profile_info(conversation_text)
        if not extracted:
            return
        for field in ["role", "current_situation", "emotional_state"]:
            if extracted.get(field):
                self.mind.update_profile(**{field: extracted[field]})
        for goal in extracted.get("new_goals", []):
            if goal and isinstance(goal, str):
                self.mind.add_goal(goal, priority=1)
        for ab in extracted.get("new_abilities", []):
            if isinstance(ab, dict) and ab.get("name"):
                self.mind.add_ability(ab["name"], ab.get("level", "beginner"))

    def _build_dashboard(self) -> str:
        profile = self.mind.get_profile()
        goals = self.mind.list_goals("active")
        gaps = self.mind.list_gaps(resolved=False)
        abilities = self.mind.list_abilities()
        insights = self.mind.list_insights()

        lines = ["=" * 50, "  [3hmind 统一智能体仪表盘]", "=" * 50, "",
                  "[个人画像]:", f"  角色: {profile.get('role', '未设置')}",
                  f"  处境: {profile.get('current_situation', '未描述')}",
                  f"  情绪: {profile.get('emotional_state', '未记录')}", "",
                  "[活跃目标]:"]
        for g in goals:
            bar = "#" * (g["progress"] // 10) + "-" * (10 - g["progress"] // 10)
            lines.append(f"  [{bar}] {g['goal']} ({g['progress']}%)")
        if not goals:
            lines.append("  (无)")

        lines.extend(["", "[能力项]:"])
        for a in abilities:
            lines.append(f"  - {a['name']} ({a['level']})")
        if not abilities:
            lines.append("  (无)")

        lines.extend(["", "[能力差距]:"])
        for g in gaps:
            lines.append(f"  - {g['area']}: {g.get('current_level', g.get('current', ''))} → "
                         f"{g.get('target_level', g.get('target', ''))} [{g['severity']}]")
        if not gaps:
            lines.append("  (无)")

        lines.extend(["", f"[沉淀经验]: {len(insights)}条"])

        topics = self.list_topics()
        if topics:
            lines.extend(["", "[话题记忆库]:"])
            for t in topics[:8]:
                stars = "★" * (t.get("priority", 1) // 2) + "☆" * (5 - t.get("priority", 1) // 2)
                lines.append(f"  [{stars}] {t['name']}: {t['entries']}条 | {t.get('summary', '')[:50]}")

        lines.append("=" * 50)
        return "\n".join(lines)

    def startup(self) -> str:
        status = self.interaction.profile_status()
        if not status["complete"]:
            question = self.reasoning.generate_discovery_question()
            return f"欢迎回来！\n\n[画像探索] {question}"
        return "欢迎回来！有什么想聊的？"


# ==================== 兼容适配器 (旧 API → 新层) ====================

class _PerceptionCompat:
    """PerceptionLayer 兼容适配 → IntentParser"""
    def __init__(self, mind, intent_parser):
        self.mind = mind
        self.intent_parser = intent_parser

    def assess_situation(self) -> dict:
        profile = self.mind.get_profile()
        return {
            "active_goals": len(self.mind.list_goals("active")),
            "abilities": len(self.mind.list_abilities()),
            "unresolved_gaps": len(self.mind.list_gaps(resolved=False)),
            "has_profile": bool(profile.get("role") and profile.get("current_situation")),
        }

    def analyze_emotional_trend(self) -> str:
        recent = self.mind.recent_history(10)
        if not recent:
            return "neutral"
        neg_words = ["焦虑", "压力", "累", "烦", "难受", "不开心", "迷茫"]
        pos_words = ["开心", "兴奋", "高兴", "好", "进步", "完成", "收获"]
        text = " ".join(h.get("content", "") for h in recent)
        neg = sum(1 for w in neg_words if w in text)
        pos = sum(1 for w in pos_words if w in text)
        if neg > pos * 2:
            return "low"
        if pos > neg:
            return "positive"
        return "neutral"

    def detect_gaps(self) -> list:
        gaps = self.mind.list_gaps(resolved=False)
        return [{"area": g["area"], "current": g.get("current_level", g.get("current", "")),
                 "target": g.get("target_level", g.get("target", "")), "severity": g["severity"]}
                for g in gaps]

    def should_intervene(self) -> tuple:
        gaps = self.mind.list_gaps(resolved=False)
        goals = self.mind.list_goals("active")
        if not goals:
            return (True, "无活跃目标")
        stale = [g for g in goals if g["progress"] < 20]
        if stale:
            return (True, f"{len(stale)}个目标进展缓慢")
        if len(gaps) >= 2:
            return (True, "多个能力差距未解决")
        return (False, "")


class _InteractionCompat:
    """InteractionLayer 兼容适配 → ThinkingGuide + ProgressTracker"""
    def __init__(self, mind, thinking_guide, progress_tracker):
        self.mind = mind
        self.thinking_guide = thinking_guide
        self.progress_tracker = progress_tracker

    def profile_status(self) -> dict:
        profile = self.mind.get_profile()
        filled = sum(1 for k in ["role", "current_situation", "emotional_state"] if profile.get(k))
        return {"filled": filled, "total": 3, "complete": filled >= 2, "profile": profile,
                "missing_role": not profile.get("role"),
                "missing_situation": not profile.get("current_situation")}

    def decompose_question(self, question: str) -> str:
        result = self.thinking_guide.decompose_thought(question)
        return result.get("analysis", "请思考这个问题的核心矛盾和可能的解决路径。")

    def collect_feedback(self, topic: str = "") -> str:
        prompts = ["今天的交流对你有没有启发？", "你觉得建议实操性如何？",
                   "还有什么我没问到但你觉得重要的事吗？"]
        import random
        prompt = random.choice(prompts)
        return f"关于'{topic}'，{prompt}" if topic else prompt

    def nudge(self) -> str:
        flagged = self.progress_tracker.check_goals()
        if flagged:
            return flagged[0]["suggestion"]
        return "一切都在轨道上，继续保持！"

    def greet_and_checkin(self) -> str:
        return "欢迎回来！3hmind 统一智能体已就绪。"
