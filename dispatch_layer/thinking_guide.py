"""
思维引导模块 — LLM 驱动的认知脚手架
思路拆解 / 利弊分析 / 复盘梳理 / 方案生成
"""

from openai import OpenAI
from config import settings


class ThinkingGuide:
    """提供 LLM 驱动的思维引导，帮助用户推演思考而非简单应答"""

    def __init__(self, mind=None):
        self.mind = mind
        self._client = None

    @property
    def client(self):
        if self._client is None and settings.llm_api_key:
            self._client = OpenAI(api_key=settings.llm_api_key, base_url=settings.llm_base_url)
        return self._client

    def _call_llm(self, system_prompt: str, user_prompt: str) -> str:
        if not self.client:
            return ""
        try:
            resp = self.client.chat.completions.create(
                model=settings.llm_model,
                messages=[{"role": "system", "content": system_prompt},
                          {"role": "user", "content": user_prompt}],
                max_tokens=settings.llm_max_tokens,
                temperature=settings.llm_temperature)
            return resp.choices[0].message.content
        except Exception as e:
            print(f"[ThinkingGuide LLM Error] {e}")
            return ""

    # ==================== 思路拆解 ====================

    def decompose_thought(self, topic: str) -> dict:
        """将复杂问题拆解为子问题 + 多角度分析"""
        context = self.mind.get_context_for_llm(topic) if self.mind else ""

        system_prompt = """你是思维引导教练。将用户的复杂问题拆解为可操作的思考框架。
返回格式: 先列出 3-5 个需要思考的子问题，再给出 2-3 个看待这个问题的不同视角。不超过 400 字。"""

        user_prompt = f"背景:\n{context}\n\n用户想分析: {topic}\n\n请拆解为子问题和多视角。"
        return {"analysis": self._call_llm(system_prompt, user_prompt)}

    # ==================== 利弊分析 ====================

    def analyze_pros_cons(self, option: str) -> dict:
        """对某个选项做结构化利弊分析"""
        context = self.mind.get_context_for_llm(option) if self.mind else ""

        system_prompt = """你是决策分析教练。对用户的选择做结构化利弊分析。
分三部分: 【优势】3-4 条、【劣势/风险】3-4 条、【关键权衡】1-2 句话。不超过 300 字。"""

        user_prompt = f"背景:\n{context}\n\n用户面临的选择: {option}\n\n请做利弊分析。"
        return {"analysis": self._call_llm(system_prompt, user_prompt)}

    # ==================== 复盘反思 ====================

    def generate_review(self) -> dict:
        """生成引导式复盘反思"""
        context = self.mind.get_context_for_llm("复盘") if self.mind else ""

        system_prompt = """你是复盘教练。生成一份引导式复盘，帮助用户审视进展。
包含: 进展总结、主要收获、存在障碍、下一周建议。口语化、不超过 400 字。"""

        return {"review": self._call_llm(system_prompt, f"背景:\n{context}\n\n请生成复盘报告。")}

    # ==================== 成长方案生成 ====================

    def generate_growth_plan(self, gap_area: str = "") -> dict:
        """为能力差距生成 4 阶段提升方案"""
        gaps = self.mind.list_gaps(resolved=False) if self.mind else []
        if gap_area:
            target = {"area": gap_area, "current_level": "beginner", "target_level": "proficient"}
        elif gaps:
            target = next((g for g in gaps if g.get("severity") == "high"), gaps[0])
        else:
            return {"plan": "当前无已识别差距，请先设定目标。"}

        abilities = self.mind.list_abilities() if self.mind else []

        system_prompt = """你是个人成长规划师。生成 4 阶段提升方案(基础入门/刻意练习/实战应用/输出检验)。
每阶段含: 阶段名、目标、具体行动、建议时长。不超过 500 字。"""

        user_prompt = f"""目标: {target['area']}
当前: {target.get('current_level', target.get('current', 'unknown'))}
目标: {target.get('target_level', target.get('target', 'proficient'))}
现有能力: {[f"{a['name']}({a['level']})" for a in abilities]}

请生成 4 阶段方案。"""

        plan_text = self._call_llm(system_prompt, user_prompt)
        return {"plan": plan_text, "target": target["area"]}
