from functools import lru_cache
from langchain_core.language_models.chat_models import BaseChatModel
from config.settings import settings


def _build_llm() -> BaseChatModel:
    """Instantiate the LLM based on `default_llm_provider` in settings (lazy imports for fast startup)."""
    provider = settings.default_llm_provider.lower()

    if provider == "gemini":
        if not settings.gemini_api_key:
            raise ValueError("GEMINI_API_KEY is not set in .env or environment.")
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model=settings.gemini_model,
            google_api_key=settings.gemini_api_key,
            temperature=0.1,
            max_retries=2,
            timeout=15,
        )

    if provider == "openai":
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is not set in .env or environment.")
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=settings.openai_model,
            api_key=settings.openai_api_key,
        )

    if provider == "anthropic":
        if not settings.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY is not set in .env or environment.")
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(
            model=settings.anthropic_model,
            api_key=settings.anthropic_api_key,
        )

    if provider == "mistral":
        if not settings.mistral_api_key:
            raise ValueError("MISTRAL_API_KEY is not set in .env or environment.")
        from langchain_mistralai import ChatMistralAI
        return ChatMistralAI(
            model=settings.mistral_model,
            api_key=settings.mistral_api_key,
            temperature=0.0,
            max_retries=2,
            timeout=15,
        )

    raise ValueError(
        f"Unsupported LLM provider: '{provider}'. "
        "Choose from: 'gemini', 'openai', 'anthropic', 'mistral'."
    )


@lru_cache(maxsize=1)
def get_llm() -> BaseChatModel:
    """
    Returns a cached LLM instance. The instance is created once and reused
    across all calls, avoiding repeated instantiation overhead.
    """
    return _build_llm()
