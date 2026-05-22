"""
InteractionLayer 向后兼容桥接
暴露与原 interaction_layer 相同的方法签名
"""
import random


class InteractionLayer:
    """兼容旧 InteractionLayer API"""
    def __init__(self, mind, thinking_guide=None, progress_tracker=None):
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
        if self.thinking_guide:
            result = self.thinking_guide.decompose_thought(question)
            return result.get("analysis", "")
        return "请思考这个问题的核心矛盾和可能的解决路径。"

    def collect_feedback(self, topic: str = "") -> str:
        prompts = ["今天的交流对你有没有启发？", "你觉得建议实操性如何？",
                   "还有什么我没问到但你觉得重要的事吗？"]
        prompt = random.choice(prompts)
        return f"关于'{topic}'，{prompt}" if topic else prompt

    def nudge(self) -> str:
        if self.progress_tracker:
            flagged = self.progress_tracker.check_goals()
            if flagged:
                return flagged[0]["suggestion"]
        return "一切都在轨道上，继续保持！"

    def greet_and_checkin(self) -> str:
        return "欢迎回来！3hmind 统一智能体已就绪。"
