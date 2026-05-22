"""
Layer 2: 自主感知层 — 状态识别 / 差距发现 / 触发判断
"""

from datetime import datetime
from collections import Counter
from memory.memory_layer import MemoryLayer


class PerceptionLayer:
    """主动感知用户当前处境、情绪状态、能力差距，决定何时介入"""

    def __init__(self, memory: MemoryLayer):
        self.memory = memory

    SKILL_KEYWORDS = {
        "python": ["python", "编程", "开发", "代码"],
        "machine learning": ["机器学习", "ml", "模型", "算法", "ai", "人工智能"],
        "communication": ["沟通", "表达", "演讲", "汇报", "写作"],
        "leadership": ["管理", "领导", "团队", "带领", "组织"],
        "english": ["英语", "english", "外语", "口语"],
        "system design": ["架构", "系统设计", "设计", "分布式"],
        "data engineering": ["数据", "sql", "etl", "数仓", "大数据"],
        "devops": ["运维", "devops", "ci/cd", "k8s", "docker", "云原生"],
    }

    def assess_situation(self) -> dict:
        """综合评估当前处境"""
        profile = self.memory.get_profile()
        goals = self.memory.list_goals("active")
        abilities = self.memory.list_abilities()
        gaps = self.memory.list_gaps(resolved=False)

        goal_count = len(goals)
        ability_count = len(abilities)
        gap_count = len(gaps)
        has_situation = bool(profile.get("current_situation"))

        urgency = "low"
        if gap_count >= 3 or (goal_count > 0 and ability_count == 0):
            urgency = "high"
        elif gap_count >= 1 or not has_situation:
            urgency = "medium"

        return {
            "has_profile": has_situation,
            "active_goals": goal_count,
            "abilities": ability_count,
            "unresolved_gaps": gap_count,
            "urgency": urgency,
            "profile": profile,
            "gaps": gaps
        }

    def detect_gaps(self) -> list:
        """从目标与能力的对比中自动发现差距"""
        goals = self.memory.list_goals("active")
        abilities = {a["name"].lower(): a["level"] for a in self.memory.list_abilities()}
        detected = []

        for goal in goals:
            goal_text = goal["goal"].lower()
            for skill, keywords in self.SKILL_KEYWORDS.items():
                if any(kw in goal_text for kw in keywords) and skill not in abilities:
                    detected.append({
                        "area": skill,
                        "current": "unknown",
                        "target": "proficient",
                        "severity": "high" if goal["priority"] >= 2 else "medium",
                        "related_goal": goal["goal"]
                    })

        return detected

    def analyze_emotional_trend(self) -> str:
        """从历史记录中分析情绪趋势"""
        recent = self.memory.recent_history(10)
        negative_words = ["焦虑", "迷茫", "困惑", "压力", "瓶颈", "困难", "累", "无聊"]
        positive_words = ["进步", "完成", "开心", "突破", "清晰", "动力", "收获"]

        neg_count = sum(
            1 for h in recent
            if any(w in h.get("content", "") for w in negative_words)
        )
        pos_count = sum(
            1 for h in recent
            if any(w in h.get("content", "") for w in positive_words)
        )

        if neg_count > pos_count + 2:
            return "low"
        elif pos_count > neg_count + 2:
            return "high"
        return "neutral"

    def should_intervene(self) -> tuple:
        """判断是否应该主动介入，以及原因"""
        situation = self.assess_situation()
        reasons = []

        if situation["urgency"] == "high":
            reasons.append("存在多个未解决的能力差距")
        if situation["active_goals"] == 0:
            reasons.append("尚未设定成长目标")
        if not situation["has_profile"]:
            reasons.append("个人处境信息为空")
        if situation["abilities"] == 0:
            reasons.append("尚未记录能力项")

        emotion = self.analyze_emotional_trend()
        if emotion == "low":
            reasons.append("近期情绪偏低，可能需要支持")

        recent = self.memory.recent_history(1)
        if not recent or (datetime.now() - datetime.fromisoformat(
            recent[-1]["time"])).total_seconds() > 86400:
            reasons.append("超过24小时未交互")

        return (len(reasons) > 0, "; ".join(reasons) if reasons else "当前状态良好")
