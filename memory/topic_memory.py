"""
Topic Memory — 按话题分类的长期记忆存储
JSON 存话题元数据 + SQLite 存条目 + 向量检索
"""

import json
import os
from datetime import datetime
from typing import Optional

from memory.database import Database

TOPIC_DEFINITIONS = {
    "tech-architecture": {
        "name": "技术架构",
        "priority": 9,
        "keywords": [
            "架构", "系统设计", "微服务", "API", "后端", "前端", "数据库",
            "分布式", "代码", "编程", "框架", "服务器", "部署", "DevOps",
            "云计算", "容器", "k8s", "docker", "nginx", "redis", "mysql",
            "高并发", "性能优化", "重构", "设计模式", "中间件", "网关",
            "架构师", "技术选型", "服务治理", "监控", "日志", "CI",
        ],
        "system_prompt_hint": "用户关注技术架构与系统设计话题"
    },
    "career-growth": {
        "name": "职业发展",
        "priority": 8,
        "keywords": [
            "职业", "工作", "跳槽", "面试", "简历", "升职", "薪资", "转行",
            "创业", "副业", "职场", "管理", "领导力", "沟通", "汇报",
            "绩效", "裁员", "offer", "实习", "试用期", "辞职",
        ],
        "system_prompt_hint": "用户关注职业发展与职场话题"
    },
    "deep-thinking": {
        "name": "深度思考",
        "priority": 7,
        "keywords": [
            "思考", "哲学", "人生", "理想", "目标", "意义", "价值观",
            "信仰", "成长", "自我", "认知", "格局", "境界", "智慧",
            "心态", "思维", "反思", "人生规划", "生命", "未来",
        ],
        "system_prompt_hint": "用户关注深度思考与人生哲学话题"
    },
    "learning-methods": {
        "name": "学习方法",
        "priority": 6,
        "keywords": [
            "学习", "方法", "效率", "记忆", "专注", "时间管理", "读书",
            "笔记", "费曼", "番茄", "思维导图", "刻意练习", "复盘",
            "自律", "习惯", "拖延", "计划", "目标", "自控力",
        ],
        "system_prompt_hint": "用户关注学习方法与效率提升话题"
    },
    "health-wellness": {
        "name": "健康养生",
        "priority": 5,
        "keywords": [
            "健康", "运动", "跑步", "健身", "睡眠", "失眠", "入睡",
            "睡不着", "早醒", "浅睡", "做梦", "减肥", "饮食", "熬夜", "多梦", "打鼾",
            "体检", "中医", "养生", "瑜伽", "冥想", "心理", "焦虑",
            "压力", "抑郁", "情绪", "精力", "疲惫", "猝死", "脱发",
        ],
        "system_prompt_hint": "用户关注健康与身心平衡话题"
    },
    "relationships": {
        "name": "情感关系",
        "priority": 4,
        "keywords": [
            "对象", "恋爱", "感情", "婚姻", "家庭", "分手", "表白", "相亲",
            "男女朋友", "女朋友", "男朋友", "两性", "亲密关系", "吵架",
            "冷战", "复合", "前任", "择偶", "脱单", "处对象", "搞对象",
        ],
        "system_prompt_hint": "用户关注情感关系话题"
    },
    "daily-life": {
        "name": "生活日常",
        "priority": 3,
        "keywords": [
            "生活", "日常", "饮食", "旅行", "购物", "租房", "搬家", "理财",
            "保险", "驾照", "买车", "装修", "宠物", "摄影", "做饭",
            "美食", "旅游", "酒店", "机票", "快递", "外卖",
        ],
        "system_prompt_hint": "用户关注生活日常话题"
    },
    "english-learning": {
        "name": "英语学习",
        "priority": 3,
        "keywords": [
            "英语", "英文", "单词", "语法", "口语", "听力", "雅思", "托福",
            "english", "翻译", "写作", "阅读理解", "发音", "词汇", "四级",
            "六级", "专八", "考研英语", "商务英语", "口语练习",
        ],
        "system_prompt_hint": "用户关注英语学习话题"
    },
}


class TopicMemory:
    """按话题分类的长期记忆管理器（JSON元数据 + SQLite条目）"""

    def __init__(self, topics_dir: str = None, db: Database = None):
        base = os.path.dirname(os.path.abspath(__file__))
        self.topics_dir = topics_dir or os.path.join(base, "topics")
        os.makedirs(self.topics_dir, exist_ok=True)
        if db is not None:
            self.db = db
        else:
            db_path = os.path.join(os.path.dirname(base), "memory.db")
            self.db = Database(db_path)

    def _meta_filepath(self, topic_slug: str) -> str:
        return os.path.join(self.topics_dir, f"{topic_slug}.json")

    # ==================== 话题检测 ====================

    def detect_topic(self, text: str) -> Optional[str]:
        """根据文本内容自动检测所属话题（返回 topic_slug），置信度低则返回 None"""
        t = text.lower()
        scores = {}
        for slug, info in TOPIC_DEFINITIONS.items():
            score = sum(1 for kw in info["keywords"] if kw.lower() in t)
            if score > 0:
                scores[slug] = score
        if not scores:
            return None
        best = max(scores, key=scores.get)
        return best if scores[best] >= 2 else None

    def detect_topics_multi(self, text: str, top_k: int = 3) -> list:
        """返回多个匹配话题及其得分（含优先级）"""
        t = text.lower()
        scored = []
        for slug, info in TOPIC_DEFINITIONS.items():
            score = sum(1 for kw in info["keywords"] if kw.lower() in t)
            if score > 0:
                scored.append({
                    "slug": slug, "name": info["name"],
                    "score": score, "hint": info["system_prompt_hint"],
                    "priority": info.get("priority", 1),
                })
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_k]

    # ==================== 话题元数据 (JSON) ====================

    def load_meta(self, topic_slug: str) -> dict:
        """加载话题元数据（JSON）"""
        fp = self._meta_filepath(topic_slug)
        if os.path.exists(fp):
            try:
                with open(fp, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                    # 确保 priority 字段存在
                    if "priority" not in meta:
                        info = TOPIC_DEFINITIONS.get(topic_slug, {})
                        meta["priority"] = info.get("priority", 1)
                    return meta
            except (json.JSONDecodeError, IOError):
                pass
        info = TOPIC_DEFINITIONS.get(topic_slug, {})
        return {
            "topic_name": info.get("name", topic_slug),
            "topic_slug": topic_slug,
            "priority": info.get("priority", 1),
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "summary": "",
            "key_concepts": [],
        }

    def save_meta(self, meta: dict):
        """保存话题元数据（JSON）"""
        meta["updated_at"] = datetime.now().isoformat()
        fp = self._meta_filepath(meta["topic_slug"])
        with open(fp, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

    # ==================== 话题优先级 ====================

    def set_topic_priority(self, topic_slug: str, priority: int) -> dict:
        """设置话题重要性（1-10），默认值来自 TOPIC_DEFINITIONS"""
        priority = max(1, min(10, priority))
        meta = self.load_meta(topic_slug)
        meta["priority"] = priority
        self.save_meta(meta)
        return {"topic_slug": topic_slug, "priority": priority, "topic_name": meta["topic_name"]}

    def get_topic_priority(self, topic_slug: str) -> int:
        """获取话题优先级"""
        info = TOPIC_DEFINITIONS.get(topic_slug, {})
        default_priority = info.get("priority", 1)
        meta = self.load_meta(topic_slug)
        return meta.get("priority", default_priority)

    # ==================== 核心操作 ====================

    def add_entry(self, text: str, topic_slug: str = None,
                  user_input: str = "", ai_response: str = "",
                  key_points: list = None) -> Optional[str]:
        """
        添加一条记忆条目：元数据存 JSON，条目存 SQLite。
        返回实际存储的 topic_slug。
        """
        detected = topic_slug or self.detect_topic(text)
        slug = detected or "general"

        # 确保元数据存在
        meta = self.load_meta(slug)

        # 条目写入 SQLite
        self.db.add_topic_entry(
            topic_slug=slug,
            topic_name=meta["topic_name"],
            user_input=user_input[:500] if user_input else text[:500],
            ai_response_summary=ai_response[:300] if ai_response else "",
            key_points=key_points or [],
            context=text[:2000],
        )

        # 修剪旧条目（保留最近 50 条）
        count = self.db.get_topic_entry_count(slug)
        if count > 50:
            entries = self.db.get_topic_entries(slug, limit=count)
            keep_ids = [e["id"] for e in entries[-50:]]
            # 删除超出部分（通过 delete + re-add 简化，实际用 SQL）
            self.db.conn.execute(
                "DELETE FROM topic_entries WHERE topic_slug=? AND id NOT IN "
                "(SELECT id FROM topic_entries WHERE topic_slug=? ORDER BY id DESC LIMIT 50)",
                (slug, slug)
            )
            self.db.conn.commit()

        # 更新关键概念（合并并去重）
        concepts = set(meta.get("key_concepts", []))
        for pt in (key_points or []):
            if len(pt) < 30:
                concepts.add(pt)
        meta["key_concepts"] = list(concepts)[:15]

        # 自动生成摘要
        meta["summary"] = self._generate_summary(slug, meta)

        self.save_meta(meta)
        return slug

    def search(self, text: str, top_k: int = 5) -> list:
        """搜索与文本相关的话题记忆条目（高优先级话题结果加权）"""
        keywords = self._extract_keywords(text)

        relevant_slugs = []
        detected = self.detect_topic(text)
        if detected:
            relevant_slugs.append(detected)
        multi = self.detect_topics_multi(text, top_k=3)
        for m in multi:
            if m["slug"] not in relevant_slugs:
                relevant_slugs.append(m["slug"])

        results = []
        for slug in relevant_slugs:
            meta = self.load_meta(slug)
            priority = meta.get("priority", TOPIC_DEFINITIONS.get(slug, {}).get("priority", 1))
            priority_boost = 1.0 + (priority - 5) * 0.1  # priority 5 -> 1.0x, 10 -> 1.5x, 1 -> 0.6x
            entries = self.db.search_topic_entries(keywords, topic_slug=slug, top_k=top_k)
            for e in entries:
                results.append({
                    "topic_slug": slug,
                    "topic_name": meta["topic_name"],
                    "priority": priority,
                    "entry": {
                        "id": e["id"],
                        "timestamp": e.get("timestamp", ""),
                        "user_input": e.get("user_input", "")[:300],
                        "ai_response_summary": e.get("ai_response_summary", ""),
                        "key_points": e.get("key_points", []),
                        "context": e.get("context", ""),
                    },
                    "score": e.get("score", 1) * priority_boost,
                })
            if meta.get("summary"):
                results.append({
                    "topic_slug": slug,
                    "topic_name": meta["topic_name"],
                    "priority": priority,
                    "summary": meta["summary"],
                    "key_concepts": meta.get("key_concepts", []),
                    "score": 0.5 * priority_boost,
                })

        results.sort(key=lambda x: x["score"], reverse=True)
        seen = set()
        deduped = []
        for r in results:
            key = r.get("summary", "") or str(r.get("entry", {}).get("id", ""))
            if key not in seen:
                seen.add(key)
                deduped.append(r)
        return deduped[:top_k]

    def get_context_for_llm(self, text: str) -> str:
        """获取与当前对话相关的记忆上下文，用于注入 LLM prompt（高优先级话题优先）"""
        results = self.search(text, top_k=3)
        if not results:
            return ""
        lines = ["[相关历史记忆]"]
        for r in results:
            priority_mark = "★" * (r.get("priority", 1) // 3) if r.get("priority", 0) >= 6 else ""
            if "summary" in r:
                lines.append(f"- [{r['topic_name']}]{priority_mark} {r['summary']}")
            if "entry" in r:
                e = r["entry"]
                pts = "；".join(e.get("key_points", []))
                ts = e.get("timestamp", "")[:10] if e.get("timestamp") else ""
                lines.append(f"  [{ts}] {e.get('user_input', '')[:120]}")
                if pts:
                    lines.append(f"  要点: {pts}")
        return "\n".join(lines)

    def list_all_topics(self) -> list:
        """列出所有已有记忆的话题（按优先级降序排列）"""
        rows = self.db.list_all_topic_slugs()
        topics = []
        for r in rows:
            meta = self.load_meta(r["topic_slug"])
            slug = r["topic_slug"]
            info = TOPIC_DEFINITIONS.get(slug, {})
            topics.append({
                "slug": slug,
                "name": r.get("topic_name", meta.get("topic_name", slug)),
                "entries": r["cnt"],
                "priority": meta.get("priority", info.get("priority", 1)),
                "default_priority": info.get("priority", 1),
                "is_custom_priority": "priority" in meta and meta["priority"] != info.get("priority", 1),
                "updated_at": r.get("updated_at", ""),
                "summary": meta.get("summary", ""),
            })
        topics.sort(key=lambda x: x["priority"], reverse=True)
        return topics

    def get_topic_for_agent(self, topic_slug: str) -> Optional[dict]:
        """获取某个话题的完整数据（供 agent 使用）"""
        meta = self.load_meta(topic_slug)
        entries = self.db.get_topic_entries(topic_slug, limit=5)
        if not entries:
            return None
        info = TOPIC_DEFINITIONS.get(topic_slug, {})
        return {
            "name": meta["topic_name"],
            "slug": topic_slug,
            "summary": meta.get("summary", ""),
            "key_concepts": meta.get("key_concepts", []),
            "priority": meta.get("priority", info.get("priority", 1)),
            "default_priority": info.get("priority", 1),
            "recent_entries": [
                {"date": e.get("timestamp", "")[:10], "text": e.get("user_input", "")[:100],
                 "points": e.get("key_points", [])}
                for e in entries[-5:]
            ],
            "total_entries": self.db.get_topic_entry_count(topic_slug),
        }

    def optimize(self, topic_slug: str) -> dict:
        """整理优化话题记忆：去重条目、合并关键概念、更新摘要"""
        entries = self.db.get_topic_entries(topic_slug, limit=100)
        if len(entries) < 2:
            return {"status": "skip", "reason": "条目不足，无需优化"}

        old_count = len(entries)

        # 去重：合并 context 相似度 > 80% 的条目
        deduped = []
        for e in entries:
            is_dup = False
            for d in deduped:
                if self._text_similarity(e.get("context", ""), d.get("context", "")) > 0.8:
                    merged = set(d.get("key_points", []) + e.get("key_points", []))
                    d["key_points"] = list(merged)[:10]
                    d["timestamp"] = max(d.get("timestamp", ""), e.get("timestamp", ""))
                    is_dup = True
                    break
            if not is_dup:
                deduped.append(e)

        if len(deduped) < old_count:
            # 有去重 — 清空重写
            self.db.delete_topic_entries(topic_slug)
            for e in deduped:
                self.db.add_topic_entry(
                    topic_slug=topic_slug,
                    topic_name=self.load_meta(topic_slug)["topic_name"],
                    user_input=e.get("user_input", ""),
                    ai_response_summary=e.get("ai_response_summary", ""),
                    key_points=e.get("key_points", []),
                    context=e.get("context", ""),
                )

        # 重新整理 key_concepts
        meta = self.load_meta(topic_slug)
        concepts = self.db.get_topic_key_concepts(topic_slug, limit=15)
        meta["key_concepts"] = concepts
        meta["summary"] = self._generate_summary(topic_slug, meta)
        self.save_meta(meta)

        return {
            "status": "optimized",
            "original_entries": old_count,
            "after_entries": len(deduped),
            "removed_duplicates": old_count - len(deduped),
            "key_concepts": concepts[:10],
        }

    # ==================== 内部辅助 ====================

    def _extract_keywords(self, text: str) -> set:
        words = set()
        for info in TOPIC_DEFINITIONS.values():
            for kw in info["keywords"]:
                if kw.lower() in text.lower():
                    words.add(kw)
        return words

    def _generate_summary(self, topic_slug: str, meta: dict) -> str:
        entries = self.db.get_topic_entries(topic_slug, limit=5)
        if not entries:
            return ""
        concepts = meta.get("key_concepts", [])
        recent_inputs = [e.get("user_input", "")[:80] for e in entries[-3:]]
        parts = []
        if concepts:
            parts.append(f"关键概念: {'、'.join(concepts[:5])}")
        if recent_inputs:
            parts.append(f"最近讨论: {'; '.join(recent_inputs)}")
        return "。".join(parts) if parts else ""

    @staticmethod
    def _text_similarity(a: str, b: str) -> float:
        """简单的文本相似度（基于字符集交集）"""
        if not a or not b:
            return 0.0
        set_a = set(a[:200])
        set_b = set(b[:200])
        if not set_a or not set_b:
            return 0.0
        return len(set_a & set_b) / len(set_a | set_b)


# 全局单例
_topic_memory_instance: Optional[TopicMemory] = None


def get_topic_memory(topics_dir: str = None, db: Database = None) -> TopicMemory:
    global _topic_memory_instance
    if _topic_memory_instance is None:
        _topic_memory_instance = TopicMemory(topics_dir, db=db)
    return _topic_memory_instance


def init_topic_memory(topics_dir: str = None, db: Database = None):
    """外部初始化话题记忆（通常由 agent 传入共享 Database）"""
    global _topic_memory_instance
    _topic_memory_instance = TopicMemory(topics_dir, db=db)
    return _topic_memory_instance
