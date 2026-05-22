"""
Layer 4: 交互执行层 — 主动对话 / 答疑拆解 / 督促执行
"""

import random
from datetime import datetime

from config import settings
from memory.memory_layer import MemoryLayer
from perception.perception_layer import PerceptionLayer


class InteractionLayer:
    """管理所有用户交互: 主动推送、问题拆解、进度跟踪、反馈收集"""

    def __init__(self, memory: MemoryLayer, perception: PerceptionLayer, reasoning=None):
        self.memory = memory
        self.perception = perception
        self.reasoning = reasoning

    def profile_status(self) -> dict:
        """检查画像完整度"""
        profile = self.memory.get_profile()
        filled = sum(1 for k in ["role", "current_situation", "emotional_state"]
                     if profile.get(k))
        return {
            "filled": filled,
            "total": 3,
            "complete": filled >= 2,
            "profile": profile,
            "missing_role": not profile.get("role"),
            "missing_situation": not profile.get("current_situation"),
        }

    def greet_and_checkin(self) -> str:
        """启动时的主动问候与状态检查"""
        situation = self.perception.assess_situation()
        intervene, reason = self.perception.should_intervene()

        lines = [
            "=" * 50,
            "  3hmind 自我成长智能体已启动",
            f"  时间: {datetime.now()}",
            "=" * 50,
            "",
            f"[状态概览]",
            f"  活跃目标: {situation['active_goals']}",
            f"  已记录能力: {situation['abilities']}",
            f"  未解决差距: {situation['unresolved_gaps']}",
            f"  综合状态: {'需要关注' if intervene else '良好'}",
        ]
        if intervene:
            lines.append(f"  [!] 介入原因: {reason}")
            lines.append("")
            lines.append(self._suggest_action(situation))
        return "\n".join(lines)

    def _suggest_action(self, situation: dict) -> str:
        if situation["active_goals"] == 0:
            return "[建议] 先设定1-2个短期成长目标"
        if not situation["has_profile"]:
            return "[建议] 告诉我你的当前处境(角色/行业/阶段)"
        if situation["unresolved_gaps"] >= 2:
            return "[建议] 你有多个未解决的能力差距，要我生成提升计划吗?"
        return "[建议] 一切都在轨道上，继续保持!"

    def ask_proactive_question(self) -> str:
        """根据当前状态生成主动提问"""
        situation = self.perception.assess_situation()
        emotion = self.perception.analyze_emotional_trend()

        if emotion == "low":
            questions = [
                "最近是否遇到了特别困扰你的事情？我可以帮你一起分析",
                "感觉你最近压力有点大，要不要停下来梳理一下当前最核心的问题？",
                "有没有什么是你想做但一直没开始的事情？",
            ]
        elif situation["active_goals"] == 0:
            questions = [
                "如果给你3个月时间来提升一项能力，你最想提升什么？",
                "回顾过去一年，你觉得最大的成长是什么？还有什么遗憾？",
                "你理想中一年后的自己是什么样的？",
            ]
        elif situation["unresolved_gaps"] >= 2:
            questions = [
                f"我注意到你有{situation['unresolved_gaps']}个待提升的能力项，最想先突破哪一个？",
                "要不要我帮你把当前的成长目标拆解成每周的具体行动？",
                "上次我们聊到的能力短板，最近有在做什么练习吗？",
            ]
        else:
            questions = [
                "最近有什么新的感悟或收获想记录下来的吗？",
                "这个月在成长目标上有哪些进展值得庆祝？",
                "有没有哪个领域你一直好奇但还没探索的？",
            ]

        return random.choice(questions)

    def decompose_question(self, question: str) -> str:
        """将复杂问题拆解为子问题"""
        lines = ["【问题拆解】为了更好地分析，请思考以下子问题:", ""]

        if any(w in question for w in ["职业", "发展", "方向", "瓶颈"]):
            lines.extend([
                "  1. 你目前的核心竞争力是什么？（列出3项）",
                "  2. 行业内未来3年最有价值的能力是什么？",
                "  3. 你距离理想岗位还差哪些硬技能和软技能？",
                "  4. 如果只选一个突破口，你会选什么？为什么？",
            ])
        elif any(w in question for w in ["技术", "编程", "学习"]):
            lines.extend([
                "  1. 你现在的技术水平在哪个阶段？（入门/熟练/精通）",
                "  2. 你学习新技术的最大障碍是什么？",
                "  3. 有没有一个具体的项目可以驱动你的学习？",
            ])
        elif any(w in question for w in ["效率", "时间", "拖延"]):
            lines.extend([
                "  1. 你的一天时间主要花在哪些事情上了？",
                "  2. 哪些任务对你来说最重要但总被推迟？",
                "  3. 你在什么时间段精力最充沛？",
            ])
        else:
            lines.extend([
                "  1. 这个问题的核心矛盾是什么？",
                "  2. 你已经尝试过哪些解决方法？效果如何？",
                "  3. 如果完全不受限制，你理想的解决方式是什么？",
            ])

        self.memory.add_history(
            entry_type="decompose",
            content=question,
            metadata={"topic": "问题拆解"}
        )
        return "\n".join(lines)

    def collect_feedback(self, topic: str = "") -> str:
        """收集用户反馈"""
        prompts = [
            "今天的交流对你有没有启发？有什么需要调整的地方吗？",
            "你觉得我给你的建议实操性如何？有没有哪里觉得不够具体？",
            "还有什么我没问到但你觉得很重要的事情吗？",
        ]
        prompt = random.choice(prompts)
        if topic:
            prompt = f"关于'{topic}'，" + prompt
        return prompt

    def nudge(self) -> str:
        """根据目标进度进行督促"""
        goals = self.memory.list_goals("active")
        if not goals:
            return self.ask_proactive_question()

        stale_goals = []
        for g in goals:
            created = datetime.fromisoformat(g["created_at"])
            days_since = (datetime.now() - created).days
            if days_since > 7 and g["progress"] < 30:
                stale_goals.append(g)

        if stale_goals:
            g = stale_goals[0]
            days = (datetime.now() - datetime.fromisoformat(g["created_at"])).days
            return (
                f"[提醒] 你的目标「{g['goal']}」已经设定{days}天了，"
                f"当前进度 {g['progress']}%。要不要花10分钟想想下一步行动？"
            )

        return self.ask_proactive_question()
