from src.config import settings


def test_settings_fields_exist():
    assert hasattr(settings, "database_url")
    assert hasattr(settings, "redis_url")
    assert hasattr(settings, "ollama_url")
    assert hasattr(settings, "ollama_chat_model")
    assert hasattr(settings, "ollama_embedding_model")
    assert hasattr(settings, "embedding_dim")
    assert hasattr(settings, "top_k")
