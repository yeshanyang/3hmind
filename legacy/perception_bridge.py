"""
PerceptionLayer 向后兼容桥接
暴露与原 perception_layer 相同的方法签名
"""


class PerceptionLayer:
    """兼容旧 PerceptionLayer API，数据取自 mind_layer"""
    def __init__(self, mind):
        self.mind = mind

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
        goals = self.mind.list_goals("active")
        if not goals:
            return (True, "无活跃目标")
        stale = [g for g in goals if g["progress"] < 20]
        if stale:
            return (True, f"{len(stale)}个目标进展缓慢")
        return (False, "")
