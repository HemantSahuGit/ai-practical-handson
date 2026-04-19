from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    openai_api_key: str = Field(default="", validation_alias="OPENAI_API_KEY")
    database_url: str = Field(
        default="postgresql+asyncpg://app:app@127.0.0.1:5432/app",
        validation_alias="DATABASE_URL",
    )
    chroma_path: str = Field(default="./.chroma_data", validation_alias="CHROMA_PATH")
    chroma_collection: str = Field(
        default="schema_docs", validation_alias="CHROMA_COLLECTION"
    )
    cors_origins: str = Field(
        default="",
        validation_alias="CORS_ORIGINS",
        description="Comma-separated browser origins; leave empty for API-only (e.g. Postman).",
    )
    openai_chat_model: str = Field(
        default="gpt-4o-mini", validation_alias="OPENAI_CHAT_MODEL"
    )
    openai_embed_model: str = Field(
        default="text-embedding-3-small", validation_alias="OPENAI_EMBED_MODEL"
    )
    chat_history_limit: int = Field(
        default=30, ge=1, validation_alias="CHAT_HISTORY_LIMIT"
    )
    schema_retrieval_k: int = Field(
        default=5, ge=1, validation_alias="SCHEMA_RETRIEVAL_K"
    )
    agent_max_tool_rounds: int = Field(
        default=8, ge=1, validation_alias="AGENT_MAX_TOOL_ROUNDS"
    )
    include_debug_in_response: bool = Field(
        default=True, validation_alias="INCLUDE_DEBUG_IN_RESPONSE"
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
