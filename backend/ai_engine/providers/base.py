"""
Interfaz base, tipos de resultado y excepciones para proveedores de IA.

Regla de dependencias: ai_engine no importa python-docx ni docx_engine;
únicamente trabaja con el esquema del Documento Intermedio (common.document_schema).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional

from common.document_schema import AIChunkOutput, AIChunkInput


# ---------------------------------------------------------------------------
# Excepciones personalizadas de proveedores
# ---------------------------------------------------------------------------
class ProviderError(Exception):
    """Excepción base para errores de la capa de proveedores de IA."""

    error_code: str = "AI_UNAVAILABLE"

    def __init__(self, message: str, *, error_code: Optional[str] = None) -> None:
        super().__init__(message)
        if error_code is not None:
            self.error_code = error_code


class AINotConfiguredError(ProviderError):
    """El proveedor de IA no está configurado (p. ej. falta AI_API_KEY o proveedor inválido)."""

    error_code: str = "AI_NOT_CONFIGURED"


# Alias explícito con el código de contrato
AI_NOT_CONFIGURED = AINotConfiguredError


class ProviderAuthError(ProviderError):
    """Credenciales inválidas o rechazadas por el proveedor (HTTP 401 / 403)."""

    error_code: str = "AI_NOT_CONFIGURED"


class ProviderRateLimitError(ProviderError):
    """Límite de peticiones o cuota alcanzada tras agotar reintentos (HTTP 429)."""

    error_code: str = "AI_RATE_LIMIT"


class ProviderUnavailableError(ProviderError):
    """Proveedor no disponible, timeout, error de red o 5xx persistente."""

    error_code: str = "AI_UNAVAILABLE"


class InvalidModelOutputError(ProviderError):
    """La salida del modelo no es JSON válido o no cumple el esquema Pydantic AIChunkOutput."""

    error_code: str = "AI_UNAVAILABLE"


# ---------------------------------------------------------------------------
# Estructuras de resultado y métricas de uso
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class TokenUsage:
    """Conteo de tokens y metadatos de invocación devueltos por el proveedor."""

    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    model: Optional[str] = None
    provider: Optional[str] = None
    attempts: int = 1

    def __post_init__(self) -> None:
        if self.total_tokens == 0 and (self.input_tokens > 0 or self.output_tokens > 0):
            object.__setattr__(self, "total_tokens", self.input_tokens + self.output_tokens)


@dataclass(frozen=True)
class ProviderResult:
    """Resultado estandarizado de una llamada a LLMProvider.structure()."""

    output: AIChunkOutput
    usage: TokenUsage = field(default_factory=TokenUsage)


# ---------------------------------------------------------------------------
# Interfaz abstracta LLMProvider
# ---------------------------------------------------------------------------
class LLMProvider(ABC):
    """Contrato común para cualquier proveedor de IA desacoplado."""

    name: str = "base"

    @abstractmethod
    def structure(
        self,
        chunk_input: AIChunkInput,
        *,
        feedback: Optional[str] = None,
    ) -> ProviderResult:
        """
        Recibe un AIChunkInput del Documento Intermedio y devuelve un ProviderResult
        con el AIChunkOutput validado por Pydantic y las métricas de tokens en usage.
        """
        raise NotImplementedError
