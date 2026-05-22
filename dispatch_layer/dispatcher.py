"""
中央调度引擎 — 按意图分发到对应工具
工具注册表 + 规则匹配 + LLM 复杂场景覆盖
"""

from intent_layer.intent_parser import IntentResult


class TaskDispatcher:
    """中央调度引擎：接收意图 → 决定激活哪些工具 → 返回执行计划"""

    def __init__(self, mind=None):
        self.mind = mind
        self._tools = {}

    def register_tool(self, name: str, handler):
        """注册一个工具"""
        self._tools[name] = handler

    # ==================== 工具注册表 ====================

    TOOL_DEFINITIONS = {
        "plan": {"description": "生成成长方案/阶段计划", "trigger_intents": ["goal_decomposition", "learning_path"]},
        "pros_cons": {"description": "结构化利弊分析", "trigger_intents": ["decision_assistance", "career_navigation"]},
        "decompose": {"description": "复杂问题拆解为子问题", "trigger_intents": ["goal_decomposition", "decision_assistance"]},
        "reflect": {"description": "引导式复盘反思", "trigger_intents": ["emotion_awareness", "career_navigation"]},
        "track_progress": {"description": "目标进度追踪", "trigger_intents": ["goal_decomposition", "habit_management"]},
        "search": {"description": "搜索记忆库相关知识", "trigger_intents": ["learning_path"]},
        "notes": {"description": "存储关键洞察到长期记忆", "trigger_intents": ["emotion_awareness"]},
        "ask_clarification": {"description": "触发补全追问", "trigger_intents": []},
    }

    # ==================== 调度逻辑 ====================

    def dispatch(self, intent: IntentResult) -> list[dict]:
        """根据意图结果决定激活的工具列表"""
        activated = []

        # 1. 从匹配模板获取建议工具
        for tool in intent.suggested_tools:
            if tool not in [a["tool"] for a in activated]:
                activated.append({
                    "tool": tool,
                    "reason": f"模板匹配",
                    "priority": "high" if len(activated) == 0 else "normal",
                })

        # 2. 歧义检测 → 触发追问
        if intent.ambiguity.get("is_ambiguous"):
            activated.append({
                "tool": "ask_clarification",
                "reason": "用户输入模糊，需要补充信息",
                "priority": "high",
                "questions": intent.ambiguity.get("suggested_clarifications", []),
            })

        # 3. 紧急度 → 优先处理
        if intent.urgency == "high":
            for a in activated:
                a["priority"] = "high"

        # 4. 确保至少有一个行动
        if not activated:
            activated.append({
                "tool": "reflect",
                "reason": "通用复盘引导",
                "priority": "normal",
            })

        return activated

    def execute(self, intent: IntentResult, thinking_guide=None, progress_tracker=None) -> dict:
        """执行调度并收集工具输出"""
        actions = self.dispatch(intent)
        results = {"actions": actions, "outputs": {}}

        for action in actions:
            tool = action["tool"]
            output = self._run_tool(tool, intent, thinking_guide, progress_tracker)
            if output:
                results["outputs"][tool] = output

        return results

    def _run_tool(self, tool: str, intent: IntentResult, thinking_guide, progress_tracker) -> dict:
        """运行单个工具"""
        if tool == "plan" and thinking_guide:
            return thinking_guide.generate_growth_plan()
        elif tool == "pros_cons" and thinking_guide:
            return thinking_guide.analyze_pros_cons(intent.raw_text)
        elif tool == "decompose" and thinking_guide:
            return thinking_guide.decompose_thought(intent.raw_text)
        elif tool == "reflect" and thinking_guide:
            return thinking_guide.generate_review()
        elif tool == "track_progress" and progress_tracker:
            return {"report": progress_tracker.generate_status_report()}
        elif tool == "search" and self.mind:
            return {"results": self.mind.search_topics(intent.raw_text)}
        elif tool == "notes" and self.mind:
            self.mind.add_insight(topic="手动记录", insight=intent.raw_text[:200], source="dispatcher")
            return {"stored": True}
        elif tool == "ask_clarification":
            return {"questions": []}
        return {}
