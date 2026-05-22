"""
3hmind 配置模块 — 通过 .env 文件和 pydantic-settings 管理所有配置
"""

import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    # LLM API
    llm_api_key: str = os.getenv("LLM_API_KEY", "")
    llm_base_url: str = os.getenv("LLM_BASE_URL", "https://api.deepseek.com/v1")
    llm_model: str = os.getenv("LLM_MODEL", "deepseek-v4-pro")
    llm_max_tokens: int = int(os.getenv("LLM_MAX_TOKENS", "2048"))
    llm_temperature: float = float(os.getenv("LLM_TEMPERATURE", "0.7"))

    # STT (speech-to-text) — 独立配置，默认复用 LLM API
    stt_api_key: str = os.getenv("STT_API_KEY", "")
    stt_base_url: str = os.getenv("STT_BASE_URL", "")
    stt_model: str = os.getenv("STT_MODEL", "qwen3-tts-vd-2026-01-26")

    # Embedding
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "deepseek-v4-pro")
    embedding_dim: int = int(os.getenv("EMBEDDING_DIM", "1536"))

    # Memory
    db_path: str = os.getenv("DB_PATH", "memory.db")
    topic_dir: str = os.getenv("TOPIC_DIR", "")
    chroma_db_path: str = os.getenv("CHROMA_DB_PATH", "")
    consolidate_threshold: int = int(os.getenv("CONSOLIDATE_THRESHOLD", "30"))

    # Scheduler
    auto_reflect_interval_min: int = int(os.getenv("AUTO_REFLECT_INTERVAL_MIN", "60"))
    auto_nudge_interval_min: int = int(os.getenv("AUTO_NUDGE_INTERVAL_MIN", "120"))

    # Web Server
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", "8080"))

    # Auth
    jwt_secret_key: str = os.getenv("JWT_SECRET_KEY", "")
    jwt_algorithm: str = os.getenv("JWT_ALGORITHM", "HS256")
    jwt_expire_days: int = int(os.getenv("JWT_EXPIRE_DAYS", "30"))
    users_file: str = os.getenv("USERS_FILE", "data/users.json")
    default_admin_password: str = os.getenv("DEFAULT_ADMIN_PASSWORD", "")

    # Data isolation
    data_dir: str = os.getenv("DATA_DIR", "data")

    # Intent parsing (统一智能体 层2)
    intent_deep_parse_enabled: bool = os.getenv("INTENT_DEEP_PARSE_ENABLED", "true").lower() == "true"
    intent_ambiguity_threshold: float = float(os.getenv("INTENT_AMBIGUITY_THRESHOLD", "0.6"))

    # Thinking guidance (统一智能体 层4)
    thinking_guide_enabled: bool = os.getenv("THINKING_GUIDE_ENABLED", "true").lower() == "true"
    growth_template_auto_load: bool = os.getenv("GROWTH_TEMPLATE_AUTO_LOAD", "true").lower() == "true"

    # Output adaptation (统一智能体 层5)
    output_adaptive_format: bool = os.getenv("OUTPUT_ADAPTIVE_FORMAT", "true").lower() == "true"

    model_config = {"extra": "ignore"}


settings = Settings()
