"""
统一输入解析器 — 所有输入模态的单一入口
标准化文字/语音/文档/视频 → UnifiedInput
"""

from dataclasses import dataclass
from intent_layer.intent_parser import IntentParser


@dataclass
class UnifiedInput:
    raw_text: str
    modality: str = "text"          # text | voice | document | video | camera
    preprocessed_text: str = ""     # 标准化后的文本
    context_summary: str = ""       # 附加上下文（文档摘要等）


class UnifiedInputParser:
    """标准化所有输入模态 → 统一文本表示"""

    def __init__(self, intent_parser: IntentParser = None):
        self.intent_parser = intent_parser or IntentParser()

    def parse(self, text: str, context_type: str = "text", context_summary: str = "") -> UnifiedInput:
        preprocessed = self._preprocess(text, context_type, context_summary)
        return UnifiedInput(
            raw_text=text,
            modality=context_type,
            preprocessed_text=preprocessed,
            context_summary=context_summary,
        )

    def _preprocess(self, text: str, context_type: str, context_summary: str) -> str:
        """根据模态类型做预处理"""
        if context_type == "voice":
            return f"[语音输入] {text}"
        elif context_type == "document":
            return f"[文档内容] {context_summary}\n{text}"
        elif context_type == "video":
            return f"[视频描述] {context_summary}\n{text}"
        elif context_type == "camera":
            return f"[图像输入] {text}"
        return text
