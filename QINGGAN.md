一、总体思路与模块
NLU：识别用户的情绪、意图与话题要点，输出严格 JSON
DST：维护对话状态（用户画像、当前情绪、风险等级、主题偏好等）
Policy/NLG：基于状态与策略模板产出共情式回复（复述 + 共情 + 开放问题 + 小建议）
DialogManager：将上述能力串联，支持多轮对话
Safety：危机言论识别、拒答边界、敏感场景引导、Moderation 占位
Prompt 工程：few-shot、CoT、自洽性、注入防护
二、NLU：情绪 / 意图 / 话题识别（JSON 约束）
我们定义输出 JSON，且 “只输出提及字段，不输出 null”。支持字段：
emotion: {label: one of ["积极","中性","消极","焦虑","愤怒","悲伤"], confidence: int (0-100)}
intent: string（如：倾诉、寻求建议、闲聊、求助、道歉、表达感谢）
topic: string（自由文本、短语即可）
risk: {level: one of ["normal","sensitive","crisis"], reason: string}
ask: string（机器人可追问的关键问题）
并提供 few-shot 示例帮助稳定输出。