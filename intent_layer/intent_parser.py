"""
二级意图解析器 — 表层指令 + 深层动机推演
LLM 驱动的意图理解，配合关键词规则回退
"""

from dataclasses import dataclass, field
from openai import OpenAI

from config import settings
from intent_layer.growth_templates import match_templates, GROWTH_TEMPLATES
from intent_layer.ambiguity_detector import AmbiguityDetector


@dataclass
class IntentResult:
    """结构化意图解析结果"""
    surface_intent: str = ""          # 表层指令：用户说了什么
    deep_intent: str = ""             # 深层动机：用户为什么这么说
    domain: str = ""                  # 领域分类
    urgency: str = "normal"           # 紧急度: low / normal / high
    matched_templates: list = field(default_factory=list)
    ambiguity: dict = field(default_factory=dict)
    suggested_tools: list = field(default_factory=list)
    raw_text: str = ""


class IntentParser:
    """二级意图解析引擎"""

    def __init__(self):
        self._client = None

    @property
    def client(self):
        if self._client is None and settings.llm_api_key:
            self._client = OpenAI(
                api_key=settings.llm_api_key, base_url=settings.llm_base_url)
        return self._client

    # ==================== 表层解析 ====================

    def parse_surface(self, text: str) -> dict:
        """Level 1: 提取表层指令 — 关键词匹配 + 模板识别"""
        t = text.strip()
        result = {
            "domain": "general",
            "urgency": "normal",
            "is_question": t.endswith("?") or t.endswith("？") or any(
                w in t for w in ["怎么", "什么", "如何", "为什么", "能不能"]),
        }

        # 紧急信号
        if any(w in t for w in ["急", "马上", "立刻", "很急", "紧急"]):
            result["urgency"] = "high"

        # 领域匹配
        templates = match_templates(t)
        if templates:
            result["domain"] = templates[0]["slug"]
            result["matched_template"] = templates[0]["name"]

        # 情绪信号
        if any(w in t for w in ["焦虑", "压", "累", "烦", "难受"]):
            result["emotional_tone"] = "negative"
        elif any(w in t for w in ["开心", "兴奋", "高兴", "棒"]):
            result["emotional_tone"] = "positive"
        else:
            result["emotional_tone"] = "neutral"

        return result

    # ==================== 深层解析 ====================

    def parse_deep(self, text: str, profile_context: str = "") -> dict:
        """Level 2: 深层动机推演 — LLM 驱动 + 模板规则回退"""
        templates = match_templates(text)
        result = {
            "deep_motivation": "",
            "unstated_needs": [],
            "matched_templates": templates,
        }

        # 从模板推断深层动机
        if templates:
            result["deep_motivation"] = templates[0]["deep_motivations"][0]

        # LLM 深层解析
        if settings.intent_deep_parse_enabled and self.client:
            llm_result = self._llm_deep_parse(text, profile_context)
            if llm_result:
                result["deep_motivation"] = llm_result.get("deep_motivation", result["deep_motivation"])
                result["unstated_needs"] = llm_result.get("unstated_needs", [])

        return result

    def _llm_deep_parse(self, text: str, profile_context: str) -> dict:
        """用 LLM 深入分析用户意图"""
        system_prompt = """你是用户意图分析专家。分析用户输入，推断深层动机和未明说的需求。
返回严格 JSON: {"deep_motivation":"一句话概括深层动机","unstated_needs":["需求1","需求2"]}
deep_motivation 不超过30字，unstated_needs 不超过3条。只返回 JSON。"""

        user_prompt = f"用户画像:\n{profile_context[:500]}\n\n用户输入: {text}"

        try:
            resp = self.client.chat.completions.create(
                model=settings.llm_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=300, temperature=0.3)
            import re, json
            content = resp.choices[0].message.content
            match = re.search(r'\{[^}]+\}', content)
            if match:
                return json.loads(match.group())
        except Exception:
            pass
        return {}

    # ==================== 统一解析 ====================

    def parse(self, text: str, profile_context: str = "") -> IntentResult:
        """执行两级解析 + 歧义检测 + 模板匹配 → 返回统一 IntentResult"""
        surface = self.parse_surface(text)
        deep = self.parse_deep(text, profile_context)
        ambiguity = AmbiguityDetector.check(text)
        templates = deep.get("matched_templates", [])

        # 从模板收集建议工具
        suggested_tools = []
        for t in templates:
            for tool in t.get("tool_triggers", []):
                if tool not in suggested_tools:
                    suggested_tools.append(tool)

        return IntentResult(
            surface_intent=text[:200],
            deep_intent=deep.get("deep_motivation", ""),
            domain=surface["domain"],
            urgency=surface["urgency"],
            matched_templates=[t["slug"] for t in templates],
            ambiguity=ambiguity,
            suggested_tools=suggested_tools,
            raw_text=text,
        )
