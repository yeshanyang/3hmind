"""
响应构建器 — 合并分析结果 + 工具输出 + 记忆上下文 → 统一响应
"""

from intent_layer.intent_parser import IntentResult


class ResponseBuilder:
    """构建最终响应载荷"""

    @classmethod
    def build(cls, analysis: str, intent: IntentResult,
              dispatch_results: dict = None, memory_context: str = "") -> dict:
        response = {
            "analysis": analysis,
            "intent": {
                "surface": intent.surface_intent,
                "deep": intent.deep_intent,
                "domain": intent.domain,
                "urgency": intent.urgency,
            },
        }

        if dispatch_results:
            response["tools_activated"] = dispatch_results.get("actions", [])
            response["tool_outputs"] = dispatch_results.get("outputs", {})

        if intent.ambiguity.get("is_ambiguous"):
            response["clarification_needed"] = True
            response["clarification_questions"] = intent.ambiguity.get(
                "suggested_clarifications", [])

        return response
