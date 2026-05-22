"""
向量存储 — ChromaDB 语义记忆检索
使用 OpenAI 兼容 API 生成 embeddings，ChromaDB 做向量存储和 ANN 搜索
"""

import os
import json
import numpy as np
from datetime import datetime
from typing import Optional
from openai import OpenAI

import chromadb
from chromadb.config import Settings as ChromaSettings

from config import settings


class VectorStore:
    """语义向量记忆库，基于 ChromaDB + API embeddings"""

    def __init__(self, storage_path: str = "vector_memory.json"):
        self._client = None
        self._embed_client = None

        # ChromaDB 持久化路径（可通过 CHROMA_DB_PATH 环境变量覆盖）
        if settings.chroma_db_path:
            self.chroma_dir = os.path.abspath(settings.chroma_db_path)
        else:
            if storage_path.endswith(".json"):
                storage_path = storage_path[:-5]
            chroma_dir = os.path.join(os.path.dirname(storage_path) if os.path.dirname(storage_path) else ".", "chroma_db")
            self.chroma_dir = os.path.abspath(chroma_dir)
        self.storage_path = storage_path

        self._chroma_client = None
        self._collection = None

    @property
    def chroma_client(self):
        if self._chroma_client is None:
            os.makedirs(self.chroma_dir, exist_ok=True)
            self._chroma_client = chromadb.PersistentClient(
                path=self.chroma_dir,
                settings=ChromaSettings(anonymized_telemetry=False)
            )
        return self._chroma_client

    @property
    def collection(self):
        if self._collection is None:
            try:
                self._collection = self.chroma_client.get_collection("memories")
            except Exception:
                self._collection = self.chroma_client.create_collection(
                    name="memories",
                    metadata={"hnsw:space": "cosine"}
                )
        return self._collection

    @property
    def embed_client(self):
        if self._embed_client is None and settings.llm_api_key:
            self._embed_client = OpenAI(
                api_key=settings.llm_api_key,
                base_url=settings.llm_base_url
            )
        return self._embed_client

    def _embed(self, text: str) -> Optional[list]:
        """调用 API 生成文本嵌入向量"""
        if not self.embed_client:
            return None
        try:
            resp = self.embed_client.embeddings.create(
                model=settings.embedding_model,
                input=text[:8000]
            )
            return resp.data[0].embedding
        except Exception:
            return None

    def add(self, content: str, category: str = "general", metadata: dict = None) -> int:
        """添加记忆条目并生成向量存入 ChromaDB"""
        embedding = self._embed(content)
        meta = metadata or {}
        meta["category"] = category
        meta["content"] = content[:500]
        meta["created_at"] = str(datetime.now())

        entry_id = str(int(datetime.now().timestamp() * 1000000))
        try:
            self.collection.add(
                documents=[content[:2000]],
                embeddings=[embedding] if embedding else None,
                metadatas=[meta],
                ids=[entry_id]
            )
        except Exception:
            # ChromaDB 添加失败不阻塞主流程
            pass
        return entry_id

    def search(self, query: str, top_k: int = 5, threshold: float = 0.3) -> list:
        """语义搜索最相似的记忆"""
        try:
            count = self.collection.count()
            if count == 0:
                return []
        except Exception:
            return []

        query_vec = self._embed(query)
        if query_vec is None:
            return self._keyword_search(query, top_k)

        try:
            results = self.collection.query(
                query_embeddings=[query_vec],
                n_results=min(top_k * 2, 20),
                include=["documents", "metadatas", "distances"]
            )
        except Exception:
            return self._keyword_search(query, top_k)

        entries = []
        if results["ids"] and results["ids"][0]:
            for i, doc_id in enumerate(results["ids"][0]):
                distance = results["distances"][0][i] if results["distances"] else 0
                similarity = 1.0 - min(distance, 1.0)  # cosine distance → similarity
                if similarity >= threshold:
                    meta = results["metadatas"][0][i] if results["metadatas"] else {}
                    entries.append({
                        "id": doc_id,
                        "content": results["documents"][0][i] if results["documents"] else "",
                        "category": meta.get("category", "general"),
                        "metadata": meta,
                        "score": similarity,
                        "created_at": meta.get("created_at", ""),
                    })
        return entries[:top_k]

    def search_by_category(self, category: str, query: str = "", top_k: int = 5) -> list:
        """按类别过滤后搜索"""
        if not query:
            try:
                results = self.collection.get(
                    where={"category": category},
                    include=["documents", "metadatas"],
                )
                entries = []
                if results["ids"]:
                    for i, doc_id in enumerate(results["ids"]):
                        meta = results["metadatas"][i] if results["metadatas"] else {}
                        entries.append({
                            "id": doc_id,
                            "content": results["documents"][i] if results["documents"] else "",
                            "category": meta.get("category", "general"),
                            "metadata": meta,
                            "created_at": meta.get("created_at", ""),
                        })
                return entries[-top_k:]
            except Exception:
                return []

        query_vec = self._embed(query)
        if query_vec is None:
            return self._keyword_search(query, top_k)

        try:
            results = self.collection.query(
                query_embeddings=[query_vec],
                n_results=min(top_k, 20),
                where={"category": category},
                include=["documents", "metadatas", "distances"]
            )
        except Exception:
            return self._keyword_search(query, top_k)

        entries = []
        if results["ids"] and results["ids"][0]:
            for i, doc_id in enumerate(results["ids"][0]):
                meta = results["metadatas"][0][i] if results["metadatas"] else {}
                entries.append({
                    "id": doc_id,
                    "content": results["documents"][0][i] if results["documents"] else "",
                    "category": meta.get("category", "general"),
                    "metadata": meta,
                    "created_at": meta.get("created_at", ""),
                })
        return entries[:top_k]

    def _keyword_search(self, query: str, top_k: int) -> list:
        """关键词搜索回退方案"""
        try:
            results = self.collection.get(include=["documents", "metadatas"])
        except Exception:
            return []

        words = set(query.lower().split())
        scored = []
        for i, doc_id in enumerate(results.get("ids", [])):
            content = results["documents"][i] if results.get("documents") else ""
            meta = results["metadatas"][i] if results.get("metadatas") else {}
            content_lower = (content or "").lower()
            score = sum(1 for w in words if w in content_lower)
            if score > 0:
                scored.append((score, {
                    "id": doc_id,
                    "content": content,
                    "category": meta.get("category", "general"),
                    "metadata": meta,
                    "created_at": meta.get("created_at", ""),
                }))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [s[1] for s in scored[:top_k]]

    # ========== 兼容旧 API ==========

    def load(self):
        """ChromaDB 自动加载，保留方法用于兼容"""
        pass

    def save(self):
        """ChromaDB 自动持久化，保留方法用于兼容"""
        pass

    def clear(self):
        """清除所有向量记忆"""
        try:
            self.chroma_client.delete_collection("memories")
            self._collection = None
        except Exception:
            pass
