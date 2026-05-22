"""
3hmind 配置模块 — 通过 .env 文件和 pydantic-settings 管理所有配置
"""

import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    # LLM API
    llm_api_key: str = os.getenv("LLM_API_KEY", "sk-81ad204238b34e90b9217aec71dc9248")
    llm_base_url: str = os.getenv("LLM_BASE_URL", "https://api.deepseek.com/v1")
    llm_model: str = os.getenv("LLM_MODEL", "deepseek-v4-pro")
    llm_max_tokens: int = int(os.getenv("LLM_MAX_TOKENS", "2048"))
    llm_temperature: float = float(os.getenv("LLM_TEMPERATURE", "0.7"))

    # Embedding
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "deepseek-v4-pro")
    embedding_dim: int = int(os.getenv("EMBEDDING_DIM", "1536"))

    # Memory
    memory_path: str = os.getenv("MEMORY_PATH", "agent_memory.json")
    db_path: str = os.getenv("DB_PATH", "memory.db")
    topic_dir: str = os.getenv("TOPIC_DIR", "")
    vector_path: str = os.getenv("VECTOR_PATH", "vector_memory")
    chroma_db_path: str = os.getenv("CHROMA_DB_PATH", "")
    consolidate_threshold: int = int(os.getenv("CONSOLIDATE_THRESHOLD", "30"))

    # Scheduler
    auto_reflect_interval_min: int = int(os.getenv("AUTO_REFLECT_INTERVAL_MIN", "60"))
    auto_nudge_interval_min: int = int(os.getenv("AUTO_NUDGE_INTERVAL_MIN", "120"))

    # Web Server
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", "8080"))

    model_config = {"extra": "ignore"}


settings = Settings()
