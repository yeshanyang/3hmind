"""
输出适配器 — 根据交互形式自适应调整输出格式
文字 → 保留结构化格式 | 语音 → 精简去标记 | 展示 → 完整详情
"""

import re


class OutputAdapter:
    """自适应输出格式选择器"""

    @classmethod
    def adapt(cls, response: dict, modality: str = "text") -> dict:
        """根据模态类型调整输出"""
        if modality == "voice":
            return cls._for_voice(response)
        elif modality == "display":
            return cls._for_display(response)
        return cls._for_text(response)

    @classmethod
    def _for_voice(cls, response: dict) -> dict:
        """语音输出：去标记、精简、添加自然停顿"""
        for key in response:
            if isinstance(response[key], str):
                # 去掉 markdown 标记
                text = re.sub(r'[#*_~`]', '', response[key])
                text = re.sub(r'【.*?】', '', text)
                text = re.sub(r'\n{2,}', '。', text)
                text = text.replace('\n', '，')
                if len(text) > 300:
                    text = text[:300] + "。"
                response[key] = text
        return response

    @classmethod
    def _for_display(cls, response: dict) -> dict:
        """展示输出：保留完整结构"""
        return response

    @classmethod
    def _for_text(cls, response: dict) -> dict:
        """文字输出：默认格式"""
        return response
