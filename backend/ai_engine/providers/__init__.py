"""Capa de proveedores de IA desacoplados para PrettyDocs."""

from .base import (
    AI_NOT_CONFIGURED,
    AINotConfiguredError,
    InvalidModelOutputError,
    LLMProvider,
    ProviderAuthError,
    ProviderError,
    ProviderRateLimitError,
    ProviderResult,
    ProviderUnavailableError,
    TokenUsage,
)
from .openrouter import OpenRouterProvider
from .registry import get_provider, register_provider

__all__ = [
    "AI_NOT_CONFIGURED",
    "AINotConfiguredError",
    "InvalidModelOutputError",
    "LLMProvider",
    "OpenRouterProvider",
    "ProviderAuthError",
    "ProviderError",
    "ProviderRateLimitError",
    "ProviderResult",
    "ProviderUnavailableError",
    "TokenUsage",
    "get_provider",
    "register_provider",
]
