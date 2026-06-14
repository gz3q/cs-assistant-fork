from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str
    redis_url: str
    ollama_url: str
    ollama_chat_model: str
    ollama_embedding_model: str
    embedding_dim: int
    top_k: int = 3
    test_database_url: str | None = None
    discord_bot_token: str | None = None
    discord_guild_id: int | None = None


settings = Settings()
