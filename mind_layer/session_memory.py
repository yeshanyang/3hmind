"""
会话短期上下文 — 内存循环缓冲区
存储最近 N 轮对话，在会话结束时清空
"""


class SessionMemory:
    """短期会话记忆（内存中，重启自动清空）"""

    def __init__(self, max_turns: int = 20):
        self._turns: list[dict] = []
        self.max_turns = max_turns

    def add_turn(self, user_msg: str, ai_response: str, topic: str = ""):
        self._turns.append({
            "user": user_msg,
            "ai": ai_response,
            "topic": topic
        })
        if len(self._turns) > self.max_turns:
            self._turns = self._turns[-self.max_turns:]

    def get_context(self, n_turns: int = 5) -> str:
        """获取最近 N 轮对话的文本表示"""
        if not self._turns:
            return ""
        recent = self._turns[-n_turns:]
        return "\n".join(
            f"用户: {t['user'][:200]}\nAI: {t['ai'][:200]}" for t in recent
        )

    @property
    def topic_distribution(self) -> dict:
        """当前会话的话题分布"""
        from collections import Counter
        return dict(Counter(t["topic"] for t in self._turns if t["topic"]))

    def clear(self):
        self._turns.clear()

    def __len__(self):
        return len(self._turns)
