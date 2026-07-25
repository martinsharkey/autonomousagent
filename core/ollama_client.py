"""Centralized ChatOllama import with fallback."""

try:
    from langchain_ollama import ChatOllama
    print("[OK] Using langchain_ollama.ChatOllama")
except ImportError:
    try:
        from langchain_community.chat_models import ChatOllama
        print("[OK] Using langchain_community.ChatOllama")
    except ImportError:
        raise ImportError(
            "ChatOllama not found. Install: pip install langchain-ollama"
        )

__all__ = ["ChatOllama"]
