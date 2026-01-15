"""Configuración LLM con soporte multi-proveedor (OpenAI, Anthropic, Google Gemini)."""

import os
from typing import Optional, Dict, Any, TYPE_CHECKING
from enum import Enum
from langchain_core.language_models import BaseChatModel

# Importaciones lazy para evitar cargar transformers innecesariamente
if TYPE_CHECKING:
    from langchain_openai import ChatOpenAI
    from langchain_anthropic import ChatAnthropic
    from langchain_google_genai import ChatGoogleGenerativeAI


class LLMProvider(str, Enum):
    """Proveedores LLM soportados."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"


class LLMConfig:
    """Configuración LLM centralizada."""
    
    DEFAULT_MODELS = {
        LLMProvider.OPENAI: "gpt-4o-mini",
        LLMProvider.ANTHROPIC: "claude-3-5-sonnet-20241022",
        LLMProvider.GOOGLE: "gemini-2.5-flash"  # Rápido y buenos límites RPM (10 RPM)
    }
    
    DEFAULT_TEMPERATURE = 0.7 # 0.0 es determinístico, 1.0 es muy creativo
    DEFAULT_MAX_TOKENS = 1000 # equivale aprox a 750 palabras de salida
    
    def __init__(
        self,
        provider: Optional[LLMProvider] = None,
        model_name: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        api_key: Optional[str] = None,
    ):
        self.provider = provider or self._detect_provider()
        self.model_name = model_name or self.DEFAULT_MODELS[self.provider]
        self.temperature = temperature if temperature is not None else self.DEFAULT_TEMPERATURE
        self.max_tokens = max_tokens or self.DEFAULT_MAX_TOKENS
        self.api_key = api_key or self._get_api_key()
    
    def _detect_provider(self) -> LLMProvider:
        """Detecta proveedor desde variables de entorno."""
        provider_env = os.getenv("LLM_PROVIDER", "").lower()
        
        if provider_env in ("google", "gemini"):
            return LLMProvider.GOOGLE
        elif provider_env == "anthropic":
            return LLMProvider.ANTHROPIC
        elif provider_env == "openai":
            return LLMProvider.OPENAI
        
        # Detectar por API keys disponibles
        if os.getenv("GOOGLE_API_KEY"):
            return LLMProvider.GOOGLE
        elif os.getenv("OPENAI_API_KEY"):
            return LLMProvider.OPENAI
        elif os.getenv("ANTHROPIC_API_KEY"):
            return LLMProvider.ANTHROPIC
        
        # Por defecto Google (tier gratuito)
        return LLMProvider.GOOGLE
    
    def _get_api_key(self) -> Optional[str]:
        """Obtiene API key del entorno según el proveedor."""
        key_map = {
            LLMProvider.OPENAI: "OPENAI_API_KEY",
            LLMProvider.ANTHROPIC: "ANTHROPIC_API_KEY",
            LLMProvider.GOOGLE: "GOOGLE_API_KEY"
        }
        return os.getenv(key_map.get(self.provider))


def create_llm(
    provider: Optional[LLMProvider] = None,
    model_name: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    api_key: Optional[str] = None,
    streaming: bool = False,
) -> BaseChatModel:
    """Función factory para crear instancia LLM configurada."""
    config = LLMConfig(
        provider=provider,
        model_name=model_name,
        temperature=temperature,
        max_tokens=max_tokens,
        api_key=api_key,
    )
    
    if not config.api_key:
        key_name = {
            LLMProvider.OPENAI: "OPENAI_API_KEY",
            LLMProvider.ANTHROPIC: "ANTHROPIC_API_KEY",
            LLMProvider.GOOGLE: "GOOGLE_API_KEY"
        }.get(config.provider, "API_KEY")
        
        raise ValueError(
            f"API key no encontrada para {config.provider.value}. "
            f"Por favor establece la variable de entorno {key_name}."
        )
    
    # Importar y crear LLM específico del proveedor
    if config.provider == LLMProvider.OPENAI:
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=config.model_name,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            api_key=config.api_key,
            streaming=streaming,
            max_retries=0,
            **config.extra_params
        )
    
    elif config.provider == LLMProvider.ANTHROPIC:
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(
            model=config.model_name,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            api_key=config.api_key,
            streaming=streaming,
            max_retries=0,
        )
    
    elif config.provider == LLMProvider.GOOGLE:
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model=config.model_name,
            temperature=config.temperature,
            max_output_tokens=config.max_tokens,
            google_api_key=config.api_key,
            max_retries=0,
        )
    
    else:
        raise ValueError(f"Proveedor no soportado: {config.provider}")

