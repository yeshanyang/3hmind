"""
意图歧义检测器 — 判断用户输入是否过于模糊
触发补全追问，让 AI 更像人一样承接不完整的想法
"""


class AmbiguityDetector:
    """检测用户输入的歧义程度，生成补全追问"""

    # 模糊信号词：出现越多，越可能歧义
    VAGUE_SIGNALS = [
        "不知道", "不确定", "可能", "好像", "大概", "应该",
        "怎么办", "怎么搞", "不太清楚", "没想好", "不太行",
    ]

    # 过短且无具体信息的模式
    SHORT_VAGUE_PATTERNS = [
        "怎么办", "帮帮我", "不行", "好难", "好累", "迷茫",
        "好烦", "我好", "怎么", "我好难", "我好累",
    ]

    @classmethod
    def check(cls, text: str) -> dict:
        """检测歧义程度，返回 {is_ambiguous, missing_info, suggested_clarifications}"""
        t = text.strip()
        result = {"is_ambiguous": False, "missing_info": [], "suggested_clarifications": []}

        # 信号 1: 过短输入
        if len(t) < 8:
            result["is_ambiguous"] = True
            result["missing_info"].append("输入过短，缺乏足够背景")
            result["suggested_clarifications"].append("能再多说一点具体情况吗？")

        # 信号 2: 模糊短语匹配
        vague_count = sum(1 for s in cls.VAGUE_SIGNALS if s in t)
        if vague_count >= 2:
            result["is_ambiguous"] = True
            result["missing_info"].append("用户表达模糊，缺乏具体细节")

        # 信号 3: 短模糊模式精准匹配
        for pat in cls.SHORT_VAGUE_PATTERNS:
            if t == pat or t.startswith(pat) and len(t) < 15:
                result["is_ambiguous"] = True
                result["missing_info"].append("仅为情绪表达，缺乏具体情境")
                break

        # 生成具体追问
        if result["is_ambiguous"]:
            if "输入过短" in str(result["missing_info"]):
                result["suggested_clarifications"].append("你现在最想聊的具体是什么？")
            if "模糊" in str(result["missing_info"]):
                result["suggested_clarifications"].append("能举一个具体的例子吗？")
            if "情绪" in str(result["missing_info"]):
                result["suggested_clarifications"].append("是什么事情让你有这样的感觉？")

        return result
