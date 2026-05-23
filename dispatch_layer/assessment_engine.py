"""
目标达成评估引擎 — 专家规则 + 学习闭环 + 百分比量化
核心: 目标→4维拆解→规则引擎判定→加权综合评分→反馈改进→迭代验证
"""

import json
from datetime import datetime


class AssessmentEngine:
    """专家系统评估引擎 — 规则驱动 + LLM辅助 + 数据量化"""

    # ── 标准权重配比 ──
    DEFAULT_WEIGHTS = {
        "知识掌握": 0.40,
        "学习进度": 0.30,
        "复盘迭代": 0.20,
        "深度思考": 0.10,
    }

    # ── 维度判定规则库（满分标准、扣分规则、阈值）──
    RULES = {
        "知识掌握": {
            "max": 100,
            "pass_threshold": 60,
            "criteria": {
                "excellent": (90, "知识体系完整，核心概念理解深刻，能举一反三"),
                "good": (75, "大部分知识点掌握，少数概念理解不够深入"),
                "pass": (60, "基础知识覆盖尚可，存在明显知识盲区"),
                "weak": (35, "知识点掌握率低，核心概念模糊"),
                "none": (0, "未开始学习或完全未掌握"),
            },
            "scoring_factors": [
                ("knowledge_coverage", 0.5, "知识点覆盖率", "已掌握知识点 / 目标总知识点"),
                ("comprehension_depth", 0.3, "理解深度", "能否正确解释核心概念并举例"),
                ("retention_rate", 0.2, "记忆保持", "复习测试中正确率"),
            ],
        },
        "学习进度": {
            "max": 100,
            "pass_threshold": 60,
            "criteria": {
                "excellent": (90, "按计划完成学习，效率高，时间利用充分"),
                "good": (75, "主要内容已完成，少量内容延期"),
                "pass": (60, "进度过半，但整体推进偏慢"),
                "weak": (30, "进度严重滞后，学习节奏不规律"),
                "none": (0, "尚未开始学习"),
            },
            "scoring_factors": [
                ("content_completion", 0.6, "内容完成度", "已完成内容 / 计划总内容"),
                ("time_efficiency", 0.2, "时间效率", "实际用时与计划用时偏差比"),
                ("consistency", 0.2, "学习规律性", "每周学习频次和时长稳定性"),
            ],
        },
        "复盘迭代": {
            "max": 100,
            "pass_threshold": 50,
            "criteria": {
                "excellent": (90, "多次有效复盘，发现并修正关键错误，产出改进方案"),
                "good": (75, "有规律复盘习惯，能发现问题和提出改进"),
                "pass": (50, "有复盘记录但质量一般，纠错不够深入"),
                "weak": (25, "几乎没有复盘，或复盘流于形式"),
                "none": (0, "无任何复盘行为"),
            },
            "scoring_factors": [
                ("review_count", 0.3, "复盘次数", "有效复盘 >= 2次为满分起点"),
                ("correction_quality", 0.4, "纠错质量", "发现并修正的错误数量和深度"),
                ("improvement_output", 0.3, "改进产出", "基于复盘产出的改进计划/实践"),
            ],
        },
        "深度思考": {
            "max": 100,
            "pass_threshold": 50,
            "criteria": {
                "excellent": (90, "有原创见解，能系统性拆解问题，拓展延伸思考"),
                "good": (70, "有独立思考输出，能对问题做出结构化的分析"),
                "pass": (50, "能回答追问，有一定思考但不是特别深入"),
                "weak": (25, "思考停留在表面，缺乏深度和原创性"),
                "none": (0, "无独立思考输出"),
            },
            "scoring_factors": [
                ("original_insight", 0.4, "原创见解", "独立提出的观点、方案、见解数量与质量"),
                ("problem_decomposition", 0.3, "问题拆解", "将复杂问题拆为子问题的能力"),
                ("extension_thinking", 0.3, "拓展延伸", "从当前话题延展到相关领域的能力"),
            ],
        },
    }

    def __init__(self, db, reasoning=None):
        self.db = db
        self.reasoning = reasoning

    # ==================== 评估管线 ====================

    def assess_goal(self, goal_id: int, phase: str = "baseline") -> dict:
        """对指定目标执行完整评估"""
        self.db.seed_goal_dimensions(goal_id)
        dims = self.db.get_goal_dimensions(goal_id)

        dim_scores = {}
        weaknesses = []
        suggestions = []

        for d in dims:
            score, feedback = self._score_dimension(goal_id, d)
            dim_scores[d["name"]] = {"score": score, "weight": d["weight"], "feedback": feedback}
            if score < self.RULES.get(d["name"], {}).get("pass_threshold", 50):
                weaknesses.append({"dimension": d["name"], "score": score,
                                   "threshold": self.RULES[d["name"]]["pass_threshold"],
                                   "gap": self.RULES[d["name"]]["pass_threshold"] - score})
                suggestions.append(self._generate_suggestion(d["name"], score))

        composite = self._calc_composite(dim_scores)
        feedback_text = self._build_feedback(composite, weaknesses, suggestions)

        record_id = self.db.add_assessment_record(
            goal_id=goal_id, phase=phase, dimension_scores=dim_scores,
            composite_score=composite, weaknesses=weaknesses,
            suggestions=suggestions, feedback_text=feedback_text)

        # 同步更新 goals 表的 progress 字段
        self.db.update_goal_progress(goal_id, int(composite))

        return {
            "record_id": record_id,
            "goal_id": goal_id,
            "phase": phase,
            "dimension_scores": dim_scores,
            "composite_score": round(composite, 1),
            "weaknesses": weaknesses,
            "suggestions": suggestions,
            "feedback": feedback_text,
        }

    def assess_with_llm(self, goal_id: int, phase: str = "baseline",
                         user_content: str = "") -> dict:
        """LLM 辅助评估 — 让 AI 对用户输出进行定性分析后结合规则引擎打分"""
        if not self.reasoning:
            return self.assess_goal(goal_id, phase)

        dims = self.db.get_goal_dimensions(goal_id)
        if not dims:
            self.db.seed_goal_dimensions(goal_id)
            dims = self.db.get_goal_dimensions(goal_id)

        # 收集历史学习会话数据
        sessions = self.db.get_learning_sessions(goal_id)

        dim_scores = {}
        weaknesses = []
        suggestions = []
        all_feedbacks = []

        for d in dims:
            name = d["name"]
            rules = self.RULES.get(name, {})
            scoring_factors = rules.get("scoring_factors", [])

            # 构造 LLM 提示词
            factor_desc = "\n".join(f"- {sf[2]}: {sf[3]}" for sf in scoring_factors)
            session_text = "\n".join(
                f"[{s['session_type']}] 内容: {s.get('content','')[:200]}\n"
                f"用户回答: {s.get('user_response','')[:300]}\n"
                f"AI反馈: {s.get('ai_feedback','')[:200]}" for s in sessions[-5:]
            ) if sessions else "（无历史会话记录）"

            prompt = f"""评估维度「{name}」，满分{rules['max']}分，合格线{rules.get('pass_threshold',50)}分。

评分因子:
{factor_desc}

历史学习记录:
{session_text}

用户最新输出:
{user_content[:1500] if user_content else "（无）"}

请根据以上数据，对该维度的各因子打分(0-100)，然后返回JSON:
{{"factor_scores": {{"factor_name": score, ...}}, "total": 加权总分(0-100), "feedback": "简洁的得分说明和改进建议(不超过50字)"}}"""

            try:
                from reasoning.reasoning_layer import ReasoningLayer
                if isinstance(self.reasoning, ReasoningLayer):
                    resp = self.reasoning._call_llm(
                        "你是学习能力评估专家。严格按规则打分，只返回JSON。", prompt)
                else:
                    resp = ""
                match = __import__('re').search(r'\{[^}]+\}', resp) if resp else None
                llm_result = json.loads(match.group()) if match else {"total": 50, "feedback": ""}
            except Exception:
                llm_result = {"total": 50, "feedback": ""}

            score = max(0, min(100, int(llm_result.get("total", 50))))
            feedback = llm_result.get("feedback", "")

            dim_scores[name] = {"score": score, "weight": d["weight"], "feedback": feedback}
            if feedback:
                all_feedbacks.append(f"[{name}] {feedback}")

            if score < rules.get("pass_threshold", 50):
                weaknesses.append({"dimension": name, "score": score,
                                   "threshold": rules["pass_threshold"],
                                   "gap": rules["pass_threshold"] - score})
                suggestions.append(self._generate_suggestion(name, score))

        composite = self._calc_composite(dim_scores)
        feedback_text = self._build_feedback(composite, weaknesses, suggestions)

        record_id = self.db.add_assessment_record(
            goal_id=goal_id, phase=phase, dimension_scores=dim_scores,
            composite_score=composite, weaknesses=weaknesses,
            suggestions=suggestions, feedback_text=feedback_text)

        self.db.update_goal_progress(goal_id, int(composite))

        return {
            "record_id": record_id,
            "goal_id": goal_id,
            "phase": phase,
            "dimension_scores": dim_scores,
            "composite_score": round(composite, 1),
            "weaknesses": weaknesses,
            "suggestions": suggestions,
            "feedback": feedback_text,
        }

    # ==================== 学习闭环方法 ====================

    def start_learning_session(self, goal_id: int, content: str = "") -> dict:
        """开启学习环节 — 生成针对性问题"""
        dims = self.db.get_goal_dimensions(goal_id)
        if not dims:
            self.db.seed_goal_dimensions(goal_id)
            dims = self.db.get_goal_dimensions(goal_id)

        # 生成追问方向
        questions = []
        for d in dims:
            rules = self.RULES.get(d["name"], {})
            q = {"dimension": d["name"], "weight": d["weight"],
                 "question": f"请简述你在「{d['name']}」方面的学习进展？具体掌握了哪些内容？"}
            questions.append(q)

        self.db.add_learning_session(goal_id, "learn", content=content)
        return {"goal_id": goal_id, "phase": "learn", "questions": questions}

    def submit_answer(self, goal_id: int, user_response: str) -> dict:
        """提交学习回答 → 触发追问反馈"""
        dims = self.db.get_goal_dimensions(goal_id)

        # 生成针对性的追问
        follow_ups = []
        for d in dims:
            fu = (f"针对「{d['name']}」({d['weight']*100:.0f}%权重)："
                  f"能否更具体地说明你的掌握程度？有没有实操或案例可以分享？")
            follow_ups.append(fu)

        self.db.add_learning_session(goal_id, "answer", user_response=user_response)
        return {"goal_id": goal_id, "phase": "feedback", "follow_ups": follow_ups}

    def verify_goal(self, goal_id: int, user_content: str = "") -> dict:
        """验证环节 — 对比基线评估，判定进步"""
        baseline = self.db.get_latest_assessment(goal_id, "baseline")
        prev = self.db.get_latest_assessment(goal_id, "verify") or {}

        # 执行新一轮评估
        result = self.assess_with_llm(goal_id, "verify", user_content)
        result["baseline_score"] = baseline.get("composite_score", 0)
        result["improvement"] = round(result["composite_score"] -
                                       baseline.get("composite_score", 0), 1)

        prev_score = prev.get("composite_score", 0)
        if prev_score:
            result["vs_previous"] = round(result["composite_score"] - prev_score, 1)
            if result["vs_previous"] > 0:
                result["trend"] = "improving"
            elif result["vs_previous"] < 0:
                result["trend"] = "declining"
            else:
                result["trend"] = "stable"

        return result

    # ==================== 内部方法 ====================

    def _score_dimension(self, goal_id: int, dim: dict) -> tuple:
        """规则引擎评分：基于历史数据计算维度得分"""
        name = dim["name"]
        rules = self.RULES.get(name, {})
        factors = rules.get("scoring_factors", [])

        sessions = self.db.get_learning_sessions(goal_id)
        sessions_text = " ".join(
            (s.get("content", "") + " " + s.get("user_response", "") +
             " " + s.get("ai_feedback", "")) for s in sessions[-10:]
        ).lower()

        # 基于数据信号计算各因子得分
        factor_scores = {}
        for fname, fweight, fdesc, frule in factors:
            score = self._calc_factor_score(name, fname, sessions, sessions_text)
            factor_scores[fname] = round(score, 1)

        if not factor_scores:
            return (0, "无数据，请开始学习后重试")

        total = sum(s * w for (_, w, _, _), s in zip(factors, factor_scores.values()))
        total = max(0, min(100, total))

        # 判定等级
        for level, (threshold, desc) in sorted(
            rules.get("criteria", {}).items(),
            key=lambda x: x[1][0], reverse=True):
            if total >= threshold:
                return (round(total, 1), desc)
        return (round(total, 1), "未评估")

    def _calc_factor_score(self, dim_name: str, factor: str,
                            sessions: list, text: str) -> float:
        """根据实际数据信号计算因子得分"""
        session_count = len(sessions)

        if factor == "knowledge_coverage":
            # 有回答内容 = 有知识输出
            has_answer = sum(1 for s in sessions if s.get("user_response", "").strip())
            return min(100, has_answer * 25 + 10)

        if factor == "comprehension_depth":
            # 回答长度和关键词密度反映理解深度
            answers = [s.get("user_response", "") for s in sessions]
            total_len = sum(len(a) for a in answers)
            return min(100, max(10, total_len / 20))

        if factor == "retention_rate":
            return min(100, session_count * 15)

        if factor == "content_completion":
            # 学习会话数量反映进度
            return min(100, session_count * 20)

        if factor == "time_efficiency":
            return min(100, max(10, session_count * 10))

        if factor == "consistency":
            return min(100, max(5, session_count * 10))

        if factor == "review_count":
            reviews = [s for s in sessions if s.get("session_type") == "review"]
            return min(100, len(reviews) * 30)

        if factor == "correction_quality":
            corrections = text.count("修正") + text.count("改进") + text.count("发现")
            return min(100, corrections * 20)

        if factor == "improvement_output":
            improvements = text.count("计划") + text.count("方案") + text.count("实践")
            return min(100, improvements * 15)

        if factor == "original_insight":
            insights = text.count("我认为") + text.count("我的观点") + text.count("独特的")
            return min(100, insights * 25 + 5)

        if factor == "problem_decomposition":
            decompositions = text.count("拆解") + text.count("子问题") + text.count("步骤")
            return min(100, decompositions * 20)

        if factor == "extension_thinking":
            extensions = text.count("延伸") + text.count("拓展") + text.count("相关")
            return min(100, extensions * 20)

        return 50.0

    def _calc_composite(self, dim_scores: dict) -> float:
        """加权综合得分"""
        total = 0.0
        for name, ds in dim_scores.items():
            total += ds["score"] * ds["weight"]
        return round(total, 1)

    def _generate_suggestion(self, dim_name: str, score: float) -> dict:
        """根据维度生成改进建议"""
        suggestions_map = {
            "知识掌握": {
                "action": "系统性梳理该领域的知识图谱，列出待学知识点清单",
                "method": "使用费曼学习法：尝试用自己的话解释每个知识点",
                "resource": "推荐阅读相关文档/教程/论文，做笔记并整理思维导图",
            },
            "学习进度": {
                "action": "制定具体到周的学习计划，细分每日任务",
                "method": "使用番茄工作法，每天固定学习时间",
                "resource": "使用进度追踪工具，记录每日学习时长和内容",
            },
            "复盘迭代": {
                "action": "建立定期复盘习惯（建议每周一次）",
                "method": "复盘模板：做了什么→遇到什么问题→如何解决→学到了什么→下次如何改进",
                "resource": "记录复盘日志，定期回顾之前的复盘记录",
            },
            "深度思考": {
                "action": "对每个学习主题提出3个为什么，层层追问",
                "method": "练习将大问题拆解为可执行的子问题",
                "resource": "写作输出：定期写学习总结、技术博客或分享笔记",
            },
        }
        s = suggestions_map.get(dim_name, {
            "action": "加强该维度的学习和实践",
            "method": "记录过程并定期检查改进",
            "resource": "寻找相关学习资料和案例",
        })
        s["dimension"] = dim_name
        s["current_score"] = score
        s["target"] = self.RULES.get(dim_name, {}).get("pass_threshold", 60)
        return s

    def _build_feedback(self, composite: float, weaknesses: list, suggestions: list) -> str:
        """生成评估反馈摘要"""
        if composite >= 90:
            level = "优秀"
        elif composite >= 75:
            level = "良好"
        elif composite >= 60:
            level = "合格"
        elif composite >= 30:
            level = "待提升"
        else:
            level = "起步"

        lines = [
            f"综合达成率: {composite:.1f}% — 等级: {level}",
            "",
        ]
        if weaknesses:
            lines.append("短板:")
            for w in weaknesses:
                lines.append(f"  ⚠ {w['dimension']}: {w['score']}分 (合格线{w['threshold']}分，差距{w['gap']}分)")
            lines.append("")
        if suggestions:
            lines.append("改进建议:")
            for s in suggestions:
                lines.append(f"  ▶ {s['dimension']}: {s.get('action','')}")
                lines.append(f"    方法: {s.get('method','')}")

        return "\n".join(lines)

    # ==================== 历史查询 ====================

    def get_assessment_history(self, goal_id: int) -> list:
        records = self.db.get_assessment_history(goal_id)
        for r in records:
            try:
                r["dimension_scores"] = json.loads(r.get("dimension_scores_json", "{}"))
            except Exception:
                r["dimension_scores"] = {}
            try:
                r["weaknesses"] = json.loads(r.get("weaknesses_json", "[]"))
            except Exception:
                r["weaknesses"] = []
            try:
                r["suggestions"] = json.loads(r.get("suggestions_json", "[]"))
            except Exception:
                r["suggestions"] = []
        return records

    def get_progress_trend(self, goal_id: int) -> dict:
        """获取目标进度趋势数据"""
        records = self.get_assessment_history(goal_id)
        if not records:
            return {"trend": "no_data", "points": []}

        points = [{"phase": r["phase"], "score": r["composite_score"],
                    "time": r["created_at"]} for r in records]

        trend = "stable"
        if len(points) >= 2:
            delta = points[-1]["score"] - points[0]["score"]
            if delta > 5:
                trend = "improving"
            elif delta < -5:
                trend = "declining"

        return {"trend": trend, "points": points, "latest": points[-1]["score"] if points else 0}
