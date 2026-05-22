"""
6 大成长场景模板 — 领域专属逻辑
每个模板包含: 触发关键词、追问链、工具调度建议
"""

GROWTH_TEMPLATES = {
    "goal_decomposition": {
        "name": "目标拆解",
        "trigger_keywords": ["目标", "计划", "实现", "达成", "做到", "完成", "想做", "想学", "梦想"],
        "surface_patterns": ["怎么实现", "如何达成", "怎么做", "想做什么", "计划"],
        "deep_motivations": ["对未来的不确定感", "希望获得掌控感", "需要具体抓手"],
        "follow_up_questions": [
            "这个目标对你来说为什么重要？",
            "你之前有没有尝试过类似的目标？效果如何？",
            "如果把目标拆成3个小步骤，第一个会是什么？",
        ],
        "tool_triggers": ["plan", "track_progress"],
    },
    "emotion_awareness": {
        "name": "情绪觉察",
        "trigger_keywords": ["焦虑", "困惑", "情绪", "压力", "烦", "累", "难受", "迷茫", "不开心", "抑郁"],
        "surface_patterns": ["很焦虑", "压力大", "不开心", "迷茫", "难受"],
        "deep_motivations": ["需要被理解和看见", "寻求情绪出口", "渴望确认感"],
        "follow_up_questions": [
            "这种感觉持续多久了？有没有什么具体的事触发了它？",
            "当你感到这样的时候，身体上有什么反应？",
            "以前你遇到类似情绪时，做什么会让你好一点？",
        ],
        "tool_triggers": ["reflect", "notes"],
    },
    "habit_management": {
        "name": "习惯管控",
        "trigger_keywords": ["习惯", "拖延", "坚持", "自律", "打卡", "每天都", "老是", "总是", "改不掉"],
        "surface_patterns": ["坚持不了", "总是拖延", "改不掉", "养成习惯"],
        "deep_motivations": ["自我效能感不足", "希望建立秩序感", "对抗即时满足"],
        "follow_up_questions": [
            "你想养成的这个习惯，每天最小的可执行单元是什么？",
            "是什么时候最容易放弃？当时发生了什么？",
            "如果把这个习惯和你已经有的一个习惯绑定，会容易一些吗？",
        ],
        "tool_triggers": ["track_progress", "plan"],
    },
    "decision_assistance": {
        "name": "决策辅助",
        "trigger_keywords": ["选择", "决定", "纠结", "怎么办", "两个", "哪个", "要不要", "该不该", "犹豫"],
        "surface_patterns": ["怎么选", "要不要", "该不该", "怎么办", "纠结"],
        "deep_motivations": ["害怕选错", "对后果的不确定", "在多重价值间冲突"],
        "follow_up_questions": [
            "选了 A 会怎样？选了 B 会怎样？最坏的情况分别是什么？",
            "如果 10 年后的你回看这个决定，会怎么建议现在的你？",
            "你内心最深处的直觉倾向于哪个方向？",
        ],
        "tool_triggers": ["pros_cons", "decompose"],
    },
    "learning_path": {
        "name": "学习路径",
        "trigger_keywords": ["学习", "提升", "掌握", "入门", "技能", "知识", "看书", "考试", "考证"],
        "surface_patterns": ["怎么学", "学什么", "提升什么", "入门"],
        "deep_motivations": ["职业焦虑", "自我实现需求", "竞争压力的应对"],
        "follow_up_questions": [
            "你目前在这个领域的基础是什么样的？",
            "你更偏好哪种学习方式？（看书/做项目/看视频/跟人学）",
            "能找到一个实际项目来驱动你的学习吗？",
        ],
        "tool_triggers": ["plan", "search", "decompose"],
    },
    "career_navigation": {
        "name": "职业导航",
        "trigger_keywords": ["跳槽", "薪资", "offer", "发展", "方向", "瓶颈", "转行", "职业", "面试"],
        "surface_patterns": ["换工作", "选offer", "职业方向", "瓶颈", "天花板"],
        "deep_motivations": ["价值感缺失", "成长天花板焦虑", "经济安全需求"],
        "follow_up_questions": [
            "你最看重一份工作的哪些方面？（钱/成长/氛围/平衡）",
            "现在的工作中，你最喜欢和最不喜欢的分别是什么？",
            "如果三年后你成了这个领域的专家，回头看现在应该做什么？",
        ],
        "tool_triggers": ["pros_cons", "plan", "reflect"],
    },
}


def match_templates(text: str) -> list[dict]:
    """根据用户输入匹配最相关的成长场景模板"""
    t = text.lower()
    scored = []
    for slug, tmpl in GROWTH_TEMPLATES.items():
        kw_score = sum(1 for kw in tmpl["trigger_keywords"] if kw in t)
        pat_score = sum(2 for p in tmpl["surface_patterns"] if p in t)
        total = kw_score + pat_score
        if total > 0:
            scored.append({"slug": slug, **tmpl, "match_score": total})
    scored.sort(key=lambda x: x["match_score"], reverse=True)
    return scored[:3]
