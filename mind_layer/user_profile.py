"""
用户画像结构化读写 — 封装 profile SQLite 表
提供完整性检查和 LLM 上下文生成
"""

from mind_layer.database import Database


class UserProfile:
    """用户画像管理器，封装 profile 表操作"""

    def __init__(self, db: Database):
        self.db = db

    def get(self) -> dict:
        p = self.db.get_profile()
        if not p.get("role") and not p.get("current_situation"):
            defaults = {"role": "全栈工程师", "current_situation": "持续学习成长中"}
            self.db.update_profile(**defaults)
            p = self.db.get_profile()
        return p

    def update(self, **kwargs):
        self.db.update_profile(**kwargs)

    def is_complete(self) -> bool:
        p = self.get()
        return bool(p.get("role") and p.get("current_situation"))

    def missing_fields(self) -> list:
        p = self.get()
        missing = []
        if not p.get("role"):
            missing.append("role")
        if not p.get("current_situation"):
            missing.append("current_situation")
        return missing

    def to_context_string(self) -> str:
        p = self.get()
        parts = []
        if p.get("role"):
            parts.append(f"角色: {p['role']}")
        if p.get("current_situation"):
            parts.append(f"当前处境: {p['current_situation']}")
        if p.get("emotional_state"):
            parts.append(f"情绪状态: {p['emotional_state']}")
        return "\n".join(parts)
