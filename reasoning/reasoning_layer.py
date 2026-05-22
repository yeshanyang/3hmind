"""
Layer 3: 思考推理层 — LLM 驱动的根因分析 / 方案生成 / 复盘反思
用 OpenAI 兼容 API 替代了规则引擎
集成话题记忆：分析前自动检索相关记忆，分析后自动存储新知识
"""

import json
import random
from datetime import datetime
from collections import Counter
from openai import OpenAI

from config import settings
from memory.memory_layer import MemoryLayer
from memory.vector_store import VectorStore
from memory.topic_memory import TOPIC_DEFINITIONS
from perception.perception_layer import PerceptionLayer


class ReasoningLayer:
    """自主思考、深度分析、生成可执行的提升方案"""

    def __init__(self, memory: MemoryLayer, perception: PerceptionLayer,
                 vector_store: VectorStore = None, topic_memory = None):
        self.memory = memory
        self.perception = perception
        self.vector = vector_store
        self.topic_memory = topic_memory
        self._client = None

    @property
    def client(self):
        if self._client is None and settings.llm_api_key:
            self._client = OpenAI(
                api_key=settings.llm_api_key,
                base_url=settings.llm_base_url
            )
        return self._client

    def _call_llm(self, system_prompt: str, user_prompt: str) -> str:
        """调用 LLM API"""
        if not self.client:
            return self._fallback_analysis(user_prompt)

        try:
            resp = self.client.chat.completions.create(
                model=settings.llm_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=settings.llm_max_tokens,
                temperature=settings.llm_temperature
            )
            return resp.choices[0].message.content
        except Exception as e:
            print(f"[LLM Error] {e}, fallback to rules engine")
            return self._fallback_analysis(user_prompt)

    def _call_llm_stream(self, system_prompt: str, user_prompt: str):
        """调用 LLM API 流式返回"""
        if not self.client:
            for char in self._fallback_analysis(user_prompt):
                yield char
            return

        try:
            stream = self.client.chat.completions.create(
                model=settings.llm_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=settings.llm_max_tokens,
                temperature=settings.llm_temperature,
                stream=True
            )
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            print(f"[LLM Stream Error] {e}, fallback to rules engine")
            for char in self._fallback_analysis(user_prompt):
                yield char

    # ==================== 根因分析 ====================
    def analyze_problem(self, question: str) -> str:
        """对用户问题进行 LLM 驱动的根因分析（集成话题记忆）"""
        context = self.memory.get_all_for_context()
        similar = self._search_similar_memories(question)
        recent_topics = self._recent_topic_summary()
        emotion = self.perception.analyze_emotional_trend()
        detected = self.perception.detect_gaps()

        # 查询话题记忆上下文（含优先级排序）

        topic_context = self.topic_memory.get_context_for_llm(question)

        # 高优先级话题提示
        priority_topics = self.topic_memory.list_all_topics()
        high_priority = [t for t in priority_topics if t.get("priority", 0) >= 7]
        priority_hint = ""
        if high_priority:
            priority_hint = "\n用户核心关注领域: " + "、".join(
                f"{t['name']}(P{t['priority']})" for t in high_priority[:3]
            )

        # 自动保存检测到的差距
        for d in detected:
            self.memory.add_gap(
                area=d["area"], current_level=d["current"],
                target_level=d["target"], severity=d["severity"]
            )

        system_prompt = """你是一个自我成长教练智能体，擅长帮助用户分析问题并给出可执行的建议。
请根据用户的问题和提供的背景信息，进行结构化分析。回答格式如下：

【处境定位】
简要描述用户当前所处的位置（角色、阶段、核心矛盾）

【根因分析】
深入分析问题的根本原因，不要停留在表面

【关联经验】
如果有相关历史记录，联系过去的经验

【行动建议】
给出3-4条具体的、可执行的建议，每条建议包含 what(做什么)、why(为什么)、how(怎么做)

保持每条建议在50字以内，总共不超过500字。直接、务实，不说套话。"""

        user_prompt = f"""用户当前处境信息:
{context}

最近关注话题: {recent_topics}{priority_hint}
情绪趋势: {emotion}
感知到的能力差距: {json.dumps(detected, ensure_ascii=False) if detected else '无'}

相关历史记忆:
{similar}

话题知识库记忆:
{topic_context or '暂无相关话题记忆'}

用户的问题: {question}

请进行结构化分析。"""

        analysis = self._call_llm(system_prompt, user_prompt)

        self.memory.add_history(
            entry_type="analysis",
            content=question,
            metadata={"topic": question[:30]}
        )

        # 保存分析结果到向量存储
        if self.vector:
            self.vector.add(
                content=f"问题: {question}\n分析: {analysis[:500]}",
                category="analysis",
                metadata={"question": question, "time": str(datetime.now())}
            )

        # 自动将对话存入话题记忆
        self._store_to_topic_memory(question, analysis)

        return analysis

    def analyze_problem_stream(self, question: str):
        """流式版本的根因分析，逐 token 返回（集成话题记忆）"""
        context = self.memory.get_all_for_context()
        similar = self._search_similar_memories(question)
        recent_topics = self._recent_topic_summary()
        emotion = self.perception.analyze_emotional_trend()
        detected = self.perception.detect_gaps()

        # 查询话题记忆上下文（含优先级排序）

        topic_context = self.topic_memory.get_context_for_llm(question)
        priority_topics = self.topic_memory.list_all_topics()
        high_priority = [t for t in priority_topics if t.get("priority", 0) >= 7]
        priority_hint = ""
        if high_priority:
            priority_hint = " 核心领域: " + "、".join(
                f"{t['name']}" for t in high_priority[:3]
            )

        for d in detected:
            self.memory.add_gap(
                area=d["area"], current_level=d["current"],
                target_level=d["target"], severity=d["severity"]
            )

        system_prompt = """你是一个自我成长教练智能体。请用口语化的方式回应用户，像朋友聊天一样自然。长度控制在150字以内。直接给出核心观点和建议，不要用标记符号。"""

        user_prompt = f"""背景: {context}{priority_hint}
相关记忆: {similar}
话题知识: {topic_context or '无'}
用户说: {question}

请用口语化、自然的方式简短回应（不要超过150字），给出1-2条最核心的建议。"""

        full_response = ""
        for token in self._call_llm_stream(system_prompt, user_prompt):
            full_response += token
            yield token

        self.memory.add_history(
            entry_type="analysis",
            content=question,
            metadata={"topic": question[:30]}
        )
        if self.vector:
            self.vector.add(
                content=f"Q: {question}\nA: {full_response[:500]}",
                category="conversation",
                metadata={"question": question, "time": str(datetime.now())}
            )

        # 自动将对话存入话题记忆
        self._store_to_topic_memory(question, full_response)

    # ==================== 成长方案生成 ====================
    def generate_growth_plan(self, gap_area: str = None) -> str:
        """为指定差距或最大差距生成 LLM 驱动的成长方案"""
        gaps = self.memory.list_gaps(resolved=False)

        if not gaps:
            detected = self.perception.detect_gaps()
            for d in detected:
                self.memory.add_gap(
                    area=d["area"], current_level=d["current"],
                    target_level=d["target"], severity=d["severity"]
                )
            gaps = self.memory.list_gaps(resolved=False)

        if not gaps and gap_area:
            gaps = [{"area": gap_area, "current_level": "beginner",
                     "target_level": "proficient", "severity": "medium"}]
        if not gaps:
            return "当前没有已识别的差距，请先设定目标或描述你的情况。"

        target = gaps[0]
        for g in gaps:
            if g.get("severity") == "high":
                target = g
                break

        abilities = self.memory.list_abilities()

        system_prompt = """你是个人成长规划师。根据用户的能力差距，生成一份4阶段提升方案。
每个阶段包含: 阶段名、目标、具体行动、建议时长。方案要具体且可执行。不超过500字。"""

        user_prompt = f"""目标能力: {target['area']}
当前水平: {target.get('current_level', target.get('current', 'unknown'))}
目标水平: {target.get('target_level', target.get('target', 'proficient'))}
现有能力: {[a['name'] + '(' + a['level'] + ')' for a in abilities]}

请生成4个阶段(基础入门/刻意练习/实战应用/输出检验)的具体方案。"""

        plan_text = self._call_llm(system_prompt, user_prompt)

        # 即使 LLM 不可用，回退也会给出方案
        steps = self._parse_plan_steps(plan_text)

        self.memory.add_plan(
            title=f"提升{target['area']}能力",
            steps=steps,
            target_gap=target.get("area", "")
        )

        return f"""【成长方案】目标: {target['area']}
  当前: {target.get('current', 'unknown')} -> 目标: {target.get('target', 'proficient')}

{plan_text}"""

    def _parse_plan_steps(self, text: str) -> list:
        """从 LLM 输出中提取步骤"""
        steps = []
        for line in text.split("\n"):
            line = line.strip()
            if line and any(line.startswith(c) for c in ["阶", "1", "2", "3", "4", "-", "*", "第"]):
                steps.append(line.lstrip("-*1234.阶段 ："))
        if not steps:
            steps = [text[:200]]
        return steps[:6]

    # ==================== 复盘反思 ====================
    def reflect(self) -> str:
        """对照目标审视进展、沉淀经验"""
        goals = self.memory.list_goals("active")
        insights = self.memory.list_insights()
        recent = self.memory.recent_history(10)

        context = self.memory.get_all_for_context()

        system_prompt = """你是个人成长复盘教练。根据用户的目标进展和近期活动，生成一份简短的复盘报告。
包含: 进展总结、主要收获、存在的问题、下周建议。不超过400字。"""

        user_prompt = f"""背景:
{context}

活跃目标: {[g['goal'] + f"({g['progress']}%)" for g in goals]}
沉淀经验数: {len(insights)}
近期交互: {len(recent)}次

请生成复盘报告。"""

        reflection = self._call_llm(system_prompt, user_prompt)

        self.memory.add_insight(
            topic="复盘",
            insight=f"复盘时发现: 活跃目标{len(goals)}个",
            source="auto-reflect"
        )
        self.memory.consolidate()

        if self.vector:
            self.vector.add(
                content=f"复盘报告: {reflection[:500]}",
                category="reflection",
                metadata={"time": str(datetime.now())}
            )

        return f"""==================================================
【自主复盘】 时间: {datetime.now()}
==================================================

  [目标进展]:
{chr(10).join(f'    [{self._bar(g["progress"])}] {g["goal"]} ({g["progress"]}%)' for g in goals) if goals else '    无活跃目标'}

{reflection}
=================================================="""

    # ==================== 辅助方法 ====================
    def _search_similar_memories(self, query: str) -> str:
        if not self.vector:
            return "(向量存储未启用)"
        results = self.vector.search(query, top_k=3)
        if not results:
            return "(无相似记忆)"
        return "\n".join(
            f"- [{r['category']}] {r['content'][:200]}" for r in results
        )

    def _recent_topic_summary(self) -> str:
        recent = self.memory.recent_history(20)
        if not recent:
            return "无"
        topics = Counter(
            h.get("metadata", {}).get("topic", "其他")
            for h in recent if h.get("metadata", {}).get("topic")
        )
        return ", ".join(f"{t}({c})" for t, c in topics.most_common(5))

    # ==================== 画像提取与自动更新 ====================
    def extract_profile_info(self, conversation_text: str) -> dict:
        """从对话中提取结构化画像信息，用于自动更新"""
        current_profile = self.memory.get_profile()

        system_prompt = """你是一个用户画像分析器。从用户的对话中提取个人信息，返回JSON格式。

规则：
1. 只提取对话中明确表达的信息，不要推测
2. 如果某项信息未在对话中出现，对应字段返回空字符串
3. emotional_state 根据用户表达的情绪判断: positive/neutral/negative
4. 返回格式必须严格是: {"role":"", "current_situation":"", "emotional_state":"", "new_goals":[], "new_abilities":[]}
5. new_goals: 用户在对话中提到但尚未记录的成长目标（最多2个）
6. new_abilities: 用户在对话中提到但尚未记录的能力（格式: [{"name":"","level":""}]）"""

        user_prompt = f"""当前已存储的画像:
- role: {current_profile.get('role', '')}
- current_situation: {current_profile.get('current_situation', '')}
- emotional_state: {current_profile.get('emotional_state', '')}

用户最新对话内容:
{conversation_text[:2000]}

请提取画像信息，返回JSON。"""

        try:
            resp = self._call_llm(system_prompt, user_prompt)
            # 提取 JSON
            import re
            match = re.search(r'\{[^}]+\}', resp)
            if match:
                return json.loads(match.group())
        except Exception as e:
            print(f"[Profile Extract Error] {e}")
        return {}

    def generate_discovery_question(self) -> str:
        """生成下一个画像探索问题（当画像不完整时）"""
        current_profile = self.memory.get_profile()
        goals = self.memory.list_goals("active")
        abilities = self.memory.list_abilities()

        # 确定缺少哪些字段
        missing = []
        if not current_profile.get("role"):
            missing.append("你的职业角色/身份是什么？")
        if not current_profile.get("current_situation"):
            missing.append("你目前处于什么阶段？遇到了什么瓶颈或想要达成什么？")

        if missing:
            system_prompt = """你是友好的个人成长教练。用户画像信息还不完整，请用自然的口语提出一个引导性问题，帮助了解用户。
要求: 亲切自然, 不超过50字，只提一个问题。"""
            user_prompt = f"需要了解: {'; '.join(missing)}"
            question = self._call_llm(system_prompt, user_prompt)
            return question.strip()

        # 画像完整，问更深层的问题
        system_prompt = """你是友好的个人成长教练。请用一个开放性问题引导用户分享最近的感受或状态变化。
要求: 自然亲切，不超过50字，像朋友聊天。"""
        user_prompt = f"用户画像: role={current_profile.get('role')}, situation={current_profile.get('current_situation')}, goals={[g['goal'] for g in goals]}, abilities={[a['name'] for a in abilities]}"
        question = self._call_llm(system_prompt, user_prompt)
        return question.strip()

    # ==================== AI 主动追问 ====================
    def generate_follow_up_question(self, last_user_msg: str = "",
                                     last_ai_response: str = "") -> str:
        """根据对话上下文生成自然的追问，驱动对话继续（优先围绕核心话题）"""
        profile = self.memory.get_profile()
        goals = self.memory.list_goals("active")
        gaps = self.memory.list_gaps(resolved=False)

        # 获取高优先级话题作为追问方向提示

        all_topics = self.topic_memory.list_all_topics()
        priority_topics = [t for t in all_topics if t.get("priority", 0) >= 6]
        topic_hint = ""
        if priority_topics:
            topic_hint = f"建议围绕核心话题追问: {'、'.join(t['name'] for t in priority_topics[:3])}"

        system_prompt = """你是一个善于引导对话的成长教练。根据上一轮对话内容，提出一个自然的追问，
让用户继续深入思考或分享更多信息。追问要像朋友聊天一样自然，有来有回。

规则：
1. 基于上一轮对话内容追问，不要跳到无关话题
2. 口语化、自然，不超过40字
3. 追问方向：深入了解用户感受、引导用户展开具体细节、或挑战用户思考
4. 不要重复用户刚刚说过的话
5. 只返回追问内容本身，不要加任何前缀或说明"""

        user_prompt = f"""用户画像: role={profile.get('role', '未知')}, situation={profile.get('current_situation', '未知')}
活跃目标: {[g['goal'] for g in goals] if goals else '无'}
能力差距: {[g['area'] for g in gaps] if gaps else '无'}
{topic_hint}

用户刚说: {last_user_msg[:300] if last_user_msg else '(无)'}
AI 刚回复: {last_ai_response[:300] if last_ai_response else '(无)'}

请生成一个自然的追问（40字以内）："""

        question = self._call_llm(system_prompt, user_prompt)
        return question.strip()

    # ==================== 追问链 (Inquiry Chain) ====================

    def generate_question_chain(self, topic: str = "") -> list:
        """生成 4-6 条渐进式追问链，用于深度对话模式"""
        profile = self.memory.get_profile()
        goals = self.memory.list_goals("active")
        gaps = self.memory.list_gaps(resolved=False)
        abilities = self.memory.list_abilities()

        # 获取高优先级话题作为主题提示
        all_topics = self.topic_memory.list_all_topics()
        priority_topics = [t for t in all_topics if t.get("priority", 0) >= 7]

        system_prompt = """你是一个专业的成长教练。根据用户的情况，设计一条渐进式追问链（4-6个问题），
用于一次深度对话。问题要像真人教练一样，逐层深入。

规则：
1. 问题从浅入深：先了解现状 → 再挖掘感受/障碍 → 然后引导反思 → 最后明确行动
2. 每个问题口语化、简短（20-50字），适合语音朗读
3. 前后问题要有逻辑递进关系
4. 围绕一个核心主题（用户的目标/差距/处境），优先围绕核心关注领域展开
5. 返回JSON数组，格式：[{"text": "问题内容", "purpose": "这个问题想了解什么"}]
6. 直接返回JSON，不要加任何前缀或代码块标记"""

        user_prompt = f"""用户画像: role={profile.get('role', '未知')}, situation={profile.get('current_situation', '未知')}
活跃目标: {[g['goal'] for g in goals] if goals else '无'}
能力差距: {[g['area'] + '(' + g.get('severity', '') + ')' for g in gaps] if gaps else '无'}
已有能力: {[a['name'] + '(' + a['level'] + ')' for a in abilities] if abilities else '无'}
核心关注领域: {[f"{t['name']}(P{t['priority']})" for t in priority_topics[:3]] if priority_topics else '根据画像推断'}
{"核心主题: " + topic if topic else "主题: 优先从用户核心关注领域或最大能力差距中选择"}

请生成4-6个渐进式追问（JSON数组格式）："""

        try:
            resp = self._call_llm(system_prompt, user_prompt)
            import re
            match = re.search(r'\[[\s\S]*\]', resp)
            if match:
                questions = json.loads(match.group())
                if isinstance(questions, list) and len(questions) > 0:
                    return questions[:6]
        except Exception as e:
            print(f"[Question Chain Error] {e}")

        # fallback
        return self._fallback_question_chain(topic, goals, gaps)

    def _fallback_question_chain(self, topic: str, goals: list, gaps: list) -> list:
        """规则回退：生成基础追问链"""
        target = topic
        if not target and gaps:
            target = gaps[0].get("area", "能力提升")
        if not target and goals:
            target = goals[0].get("goal", "个人成长")
        if not target:
            target = "个人成长"

        return [
            {"text": f"关于「{target}」，你目前的具体情况是怎样的？", "purpose": "了解现状"},
            {"text": "在这个过程中，你遇到的最大困难或阻碍是什么？", "purpose": "识别障碍"},
            {"text": "你觉得是什么原因导致了这些困难？有没有更深层的因素？", "purpose": "根因分析"},
            {"text": "如果完全不受限制，你理想中的状态是什么样的？", "purpose": "明确目标"},
            {"text": "接下来一个月，你能迈出的最小但最实在的一步是什么？", "purpose": "明确行动"},
        ]

    def extract_insight_from_answer(self, question: str, answer: str,
                                     context: str = "") -> str:
        """从单个 Q&A 中提取洞察点，存入记忆"""
        system_prompt = """从用户的回答中提炼一条关键洞察（1句话，不超过50字）。
洞察要反映用户的核心状态、深层需求或行动障碍。如果回答信息量不足，返回空字符串。"""
        user_prompt = f"问题: {question}\n回答: {answer[:500]}\n上下文: {context[-500:]}"
        insight = self._call_llm(system_prompt, user_prompt)
        return insight.strip()[:100]

    def summarize_inquiry(self, topic: str, context: str,
                           insights: list) -> str:
        """对整个追问会话做总结"""
        system_prompt = """你是成长教练。请对刚才的深度对话做一个简短总结（150字以内）。
包含：用户的核心状态、发现的关健洞察、建议的下一步行动。口语化、有温度。"""
        user_prompt = f"主题: {topic}\n对话记录: {context[-2000:]}\n已提炼洞察: {insights}"
        summary = self._call_llm(system_prompt, user_prompt)
        return summary.strip()

    def generate_transition_response(self, user_answer: str,
                                      next_question: str = "",
                                      is_final: bool = False) -> str:
        """生成简短过渡语，让追问之间衔接自然"""
        if is_final:
            system_prompt = """用1-2句话感谢用户的分享并自然过渡到总结。不超过30字，口语化。"""
        else:
            system_prompt = """用1句话简短回应用户的回答，然后自然引出下一个问题。不超过35字，口语化。
不要展开分析，不要给建议，只是自然过渡。"""
        user_prompt = f"用户说: {user_answer[:200]}\n下一个问题: {next_question if next_question else '总结'}"
        resp = self._call_llm(system_prompt, user_prompt)
        return resp.strip()

    def _bar(self, progress: int) -> str:
        return "#" * (progress // 10) + "-" * (10 - progress // 10)

    def _fallback_analysis(self, question: str) -> str:
        """LLM 不可用时的规则回退"""
        context = self.memory.get_all_for_context()
        gaps = self.memory.list_gaps(resolved=False)
        detected = self.perception.detect_gaps()

        q_lower = question.lower()
        suggestions = []

        if any(w in q_lower for w in ["职业", "瓶颈", "方向"]):
            suggestions = [
                "梳理当前技能树，画出能力雷达图，找到最短的木板",
                "选择一个高价值方向深耕3个月，制定周级别的里程碑",
                "每周进行一次深度复盘，记录做得好的和需要改进的各3条"
            ]
        elif any(w in q_lower for w in ["技术", "编程", "代码"]):
            suggestions = [
                "以项目驱动学习，选择一个实际项目边做边学",
                "每周阅读2篇高质量技术博客或论文精要"
            ]
        elif any(w in q_lower for w in ["效率", "时间", "拖延"]):
            suggestions = [
                "使用时间块法，每天规划3个核心任务",
                "建立晨间仪式，早起第一件事完成当天最重要的任务"
            ]
        else:
            suggestions = [
                "将当前问题拆解为3个可执行的小步骤，逐一攻克",
                "寻找该领域有经验的人交流，获取反馈",
                "建立每日微习惯，每天投入30分钟在目标能力上"
            ]

        gap_list = [g["area"] for g in (gaps or detected)]
        ability_list = [a["name"] for a in self.memory.list_abilities()]

        return f"""==================================================
【处境定位】(规则引擎)
  当前状况: {context}

【差距识别】
  能力缺口: {', '.join(gap_list) if gap_list else '暂未发现'}
  已有能力: {', '.join(ability_list) if ability_list else '尚未记录'}

【问题剖析】
  问题: {question}
  分析: 从当前处境与目标差距来看，核心在于缺乏针对性的能力储备与系统性提升路径。

【行动建议】
{chr(10).join(f'  {i+1}. {s}' for i, s in enumerate(suggestions[:4]))}
================================================="""

    # ==================== 话题记忆集成 ====================

    def _store_to_topic_memory(self, question: str, analysis: str):
        """自动将对话内容存入话题记忆"""
        try:
    
            combined = question + " " + analysis[:300]

            # 优先从用户问题检测话题（避免分析中的 profile 上下文干扰）
            detected = self.topic_memory.detect_topic(question) or self.topic_memory.detect_topic(combined)
            key_points = self._extract_key_points(combined, topic_slug=detected)

            self.topic_memory.add_entry(
                text=combined,
                topic_slug=detected,
                user_input=question,
                ai_response=analysis[:500],
                key_points=key_points,
            )

            # 定期整理（每10次对话触发一次）
            self._maybe_optimize_topics(topic_memory)
        except Exception as e:
            pass  # 话题记忆存储失败不影响主流程

    def _extract_key_points(self, text: str, topic_slug: str = None) -> list:
        """从文本中提取话题相关的关键短语"""
        points = []
        # 从对应话题定义关键词中匹配实际出现的词
        slugs_to_check = [topic_slug] if topic_slug else list(TOPIC_DEFINITIONS.keys())
        for slug in slugs_to_check:
            info = TOPIC_DEFINITIONS.get(slug, {})
            for kw in info.get("keywords", []):
                if kw.lower() in text.lower() and kw not in points:
                    points.append(kw)
        # 如果话题关键词命中少，再从文本中提取技术/领域术语
        if len(points) < 2:
            import re
            eng_terms = re.findall(r'\b[A-Za-z][A-Za-z0-9+#./-]{2,}\b', text)
            for t in eng_terms[:5]:
                if t.lower() not in {'what', 'why', 'how', 'the', 'and', 'for', 'you', 'your'}:
                    points.append(t)
        return points[:8]

    def _maybe_optimize_topics(self, topic_memory):
        """定期触发话题记忆优化"""
        import random
        if random.random() < 0.1:  # 10% 概率触发
            all_topics = self.topic_memory.list_all_topics()
            for t in all_topics:
                if t.get("entries", 0) >= 5:
                    self.topic_memory.optimize(t["slug"])

    def search_topic_memory(self, query: str) -> list:
        """对外接口：搜索话题记忆"""
        return self.topic_memory.search(query)

    def get_topic_list(self) -> list:
        """对外接口：列出所有话题"""
        return self.topic_memory.list_all_topics()

    def get_topic_detail(self, topic_slug: str) -> dict:
        """对外接口：获取话题详情"""
        return self.topic_memory.get_topic_for_agent(topic_slug)


