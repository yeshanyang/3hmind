"""
话题记忆存储 — 按话题分类的长期记忆
JSON 存话题元数据 + SQLite 存条目 + 向量检索
从 memory/topic_memory.py 重构：TopicMemory → TopicMemoryStore，TOPIC_DEFINITIONS 外置
"""

import json
import os
from datetime import datetime
from typing import Optional

from mind_layer.database import Database
from mind_layer.topic_definitions import TOPIC_DEFINITIONS


class TopicMemoryStore:
    """按话题分类的长期记忆管理器"""

    def __init__(self, topics_dir: str = None, db: Database = None):
        base = os.path.dirname(os.path.abspath(__file__))
        self.topics_dir = topics_dir or os.path.join(base, "..", "data", "topics")
        os.makedirs(self.topics_dir, exist_ok=True)
        if db is not None:
            self.db = db
        else:
            self.db = Database(os.path.join(os.path.dirname(base), "memory.db"))

    def _meta_filepath(self, topic_slug: str) -> str:
        return os.path.join(self.topics_dir, f"{topic_slug}.json")

    # ==================== 话题检测 ====================

    def detect_topic(self, text: str) -> Optional[str]:
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

    # ==================== 元数据 (JSON) ====================

    def load_meta(self, topic_slug: str) -> dict:
        fp = self._meta_filepath(topic_slug)
        if os.path.exists(fp):
            try:
                with open(fp, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                    if "priority" not in meta:
                        meta["priority"] = TOPIC_DEFINITIONS.get(topic_slug, {}).get("priority", 1)
                    return meta
            except (json.JSONDecodeError, IOError):
                pass
        info = TOPIC_DEFINITIONS.get(topic_slug, {})
        return {
            "topic_name": info.get("name", topic_slug), "topic_slug": topic_slug,
            "priority": info.get("priority", 1),
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "summary": "", "key_concepts": [],
        }

    def save_meta(self, meta: dict):
        meta["updated_at"] = datetime.now().isoformat()
        with open(self._meta_filepath(meta["topic_slug"]), "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

    # ==================== 优先级 ====================

    def set_topic_priority(self, topic_slug: str, priority: int) -> dict:
        priority = max(1, min(10, priority))
        meta = self.load_meta(topic_slug)
        meta["priority"] = priority
        self.save_meta(meta)
        return {"topic_slug": topic_slug, "priority": priority, "topic_name": meta["topic_name"]}

    def get_topic_priority(self, topic_slug: str) -> int:
        info = TOPIC_DEFINITIONS.get(topic_slug, {})
        default_priority = info.get("priority", 1)
        return self.load_meta(topic_slug).get("priority", default_priority)

    # ==================== 条目操作 ====================

    def add_entry(self, text: str, topic_slug: str = None,
                  user_input: str = "", ai_response: str = "",
                  key_points: list = None) -> Optional[str]:
        detected = topic_slug or self.detect_topic(text)
        slug = detected or "general"
        meta = self.load_meta(slug)

        self.db.add_topic_entry(
            topic_slug=slug, topic_name=meta["topic_name"],
            user_input=user_input[:500] if user_input else text[:500],
            ai_response_summary=ai_response[:300] if ai_response else "",
            key_points=key_points or [], context=text[:2000])

        # 修剪旧条目（保留最近 50 条）
        count = self.db.get_topic_entry_count(slug)
        if count > 50:
            self.db.conn.execute(
                "DELETE FROM topic_entries WHERE topic_slug=? AND id NOT IN "
                "(SELECT id FROM topic_entries WHERE topic_slug=? ORDER BY id DESC LIMIT 50)",
                (slug, slug))
            self.db.conn.commit()

        # 更新关键概念
        concepts = set(meta.get("key_concepts", []))
        for pt in (key_points or []):
            if len(pt) < 30:
                concepts.add(pt)
        meta["key_concepts"] = list(concepts)[:15]
        meta["summary"] = self._generate_summary(slug, meta)
        self.save_meta(meta)
        return slug

    def search(self, text: str, top_k: int = 5) -> list:
        keywords = self._extract_keywords(text)
        relevant_slugs = []
        detected = self.detect_topic(text)
        if detected:
            relevant_slugs.append(detected)
        for m in self.detect_topics_multi(text, top_k=3):
            if m["slug"] not in relevant_slugs:
                relevant_slugs.append(m["slug"])

        results = []
        for slug in relevant_slugs:
            meta = self.load_meta(slug)
            priority = meta.get("priority", TOPIC_DEFINITIONS.get(slug, {}).get("priority", 1))
            boost = 1.0 + (priority - 5) * 0.1
            entries = self.db.search_topic_entries(keywords, topic_slug=slug, top_k=top_k)
            for e in entries:
                results.append({
                    "topic_slug": slug, "topic_name": meta["topic_name"],
                    "priority": priority,
                    "entry": {
                        "id": e["id"], "timestamp": e.get("timestamp", ""),
                        "user_input": e.get("user_input", "")[:300],
                        "ai_response_summary": e.get("ai_response_summary", ""),
                        "key_points": e.get("key_points", []),
                        "context": e.get("context", ""),
                    },
                    "score": e.get("score", 1) * boost,
                })
            if meta.get("summary"):
                results.append({
                    "topic_slug": slug, "topic_name": meta["topic_name"],
                    "priority": priority, "summary": meta["summary"],
                    "key_concepts": meta.get("key_concepts", []),
                    "score": 0.5 * boost,
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
        results = self.search(text, top_k=3)
        if not results:
            return ""
        lines = ["[相关历史记忆]"]
        for r in results:
            mark = "★" * (r.get("priority", 1) // 3) if r.get("priority", 0) >= 6 else ""
            if "summary" in r:
                lines.append(f"- [{r['topic_name']}]{mark} {r['summary']}")
            if "entry" in r:
                e = r["entry"]
                pts = "；".join(e.get("key_points", []))
                ts = e.get("timestamp", "")[:10] if e.get("timestamp") else ""
                lines.append(f"  [{ts}] {e.get('user_input', '')[:120]}")
                if pts:
                    lines.append(f"  要点: {pts}")
        return "\n".join(lines)

    def list_all_topics(self) -> list:
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
        meta = self.load_meta(topic_slug)
        entries = self.db.get_topic_entries(topic_slug, limit=5)
        if not entries:
            return None
        info = TOPIC_DEFINITIONS.get(topic_slug, {})
        return {
            "name": meta["topic_name"], "slug": topic_slug,
            "summary": meta.get("summary", ""),
            "key_concepts": meta.get("key_concepts", []),
            "priority": meta.get("priority", info.get("priority", 1)),
            "default_priority": info.get("priority", 1),
            "recent_entries": [
                {"date": e.get("timestamp", "")[:10],
                 "text": e.get("user_input", "")[:100],
                 "points": e.get("key_points", [])}
                for e in entries[-5:]
            ],
            "total_entries": self.db.get_topic_entry_count(topic_slug),
        }

    def optimize(self, topic_slug: str) -> dict:
        entries = self.db.get_topic_entries(topic_slug, limit=100)
        if len(entries) < 2:
            return {"status": "skip", "reason": "条目不足，无需优化"}

        old_count = len(entries)
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
            self.db.delete_topic_entries(topic_slug)
            meta = self.load_meta(topic_slug)
            for e in deduped:
                self.db.add_topic_entry(
                    topic_slug=topic_slug, topic_name=meta["topic_name"],
                    user_input=e.get("user_input", ""),
                    ai_response_summary=e.get("ai_response_summary", ""),
                    key_points=e.get("key_points", []),
                    context=e.get("context", ""))

        meta = self.load_meta(topic_slug)
        concepts = self.db.get_topic_key_concepts(topic_slug, limit=15)
        meta["key_concepts"] = concepts
        meta["summary"] = self._generate_summary(topic_slug, meta)
        self.save_meta(meta)

        return {
            "status": "optimized", "original_entries": old_count,
            "after_entries": len(deduped),
            "removed_duplicates": old_count - len(deduped),
            "key_concepts": concepts[:10],
        }

    # ==================== 内部辅助 ====================

    def _extract_keywords(self, text: str) -> set:
        return {kw for info in TOPIC_DEFINITIONS.values()
                for kw in info["keywords"] if kw.lower() in text.lower()}

    def _generate_summary(self, topic_slug: str, meta: dict) -> str:
        entries = self.db.get_topic_entries(topic_slug, limit=5)
        if not entries:
            return ""
        parts = []
        concepts = meta.get("key_concepts", [])
        if concepts:
            parts.append(f"关键概念: {'、'.join(concepts[:5])}")
        recent = [e.get("user_input", "")[:80] for e in entries[-3:]]
        if recent:
            parts.append(f"最近讨论: {'; '.join(recent)}")
        return "。".join(parts) if parts else ""

    @staticmethod
    def _text_similarity(a: str, b: str) -> float:
        if not a or not b:
            return 0.0
        set_a, set_b = set(a[:200]), set(b[:200])
        if not set_a or not set_b:
            return 0.0
        return len(set_a & set_b) / len(set_a | set_b)

    def set_db(self, db: Database):
        self.db = db
