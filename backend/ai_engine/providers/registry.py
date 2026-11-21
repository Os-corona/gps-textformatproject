"""
Registro y fábrica de proveedores de IA.

Lee la configuración desde variables de entorno (.env / Django settings):
- AI_PROVIDER (por defecto: 'openrouter')
- AI_API_KEY (obligatoria para proveedores reales; si falta, lanza AINotConfiguredError / AI_NOT_CONFIGURED)
- AI_MODEL (por defecto: 'google/gemini-2.0-flash-001')
- AI_TIMEOUT_S (por defecto: 30.0)
- AI_BASE_URL (opcional, por defecto: 'https://openrouter.ai/api/v1')
- AI_TEMPERATURE (opcional, rango [0.0, 0.2], por defecto: 0.1)
"""

from __future__ import annotations

import os
from typing import Any, Callable, Dict, Optional

from .base import AINotConfiguredError, LLMProvider
from .openrouter import (
    DEFAULT_OPENROUTER_BASE_URL,
    DEFAULT_OPENROUTER_MODEL,
    DEFAULT_TEMPERATURE,
    DEFAULT_TIMEOUT_S,
    OpenRouterProvider,
)

ProviderFactory = Callable[..., LLMProvider]
_CUSTOM_PROVIDERS: Dict[str, ProviderFactory] = {}


def register_provider(name: str, factory: ProviderFactory) -> None:
    """Permite registrar proveedores adicionales (p. ej. FakeProvider en S3T7)."""
    _CUSTOM_PROVIDERS[name.strip().lower()] = factory


def _read_config_value(env_name: str, default: Optional[str] = None) -> Optional[str]:
    """Lee primero de os.environ (para soporte limpio en tests y .env) y luego de Django settings."""
    if env_name in os.environ:
        return os.environ[env_name]
    try:
        from django.conf import settings

        if settings.configured and hasattr(settings, env_name):
            val = getattr(settings, env_name)
            return None if val is None else str(val)
    except Exception:
        pass
    return default


def get_provider(
    *,
    provider_name: Optional[str] = None,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    timeout_s: Optional[float] = None,
    base_url: Optional[str] = None,
    temperature: Optional[float] = None,
    **kwargs: Any,
) -> LLMProvider:
    """
    Resuelve e instancia el proveedor de IA configurado.

    Lanza AINotConfiguredError (error_code='AI_NOT_CONFIGURED') si falta AI_API_KEY
    para un proveedor real o si AI_PROVIDER no es válido.
    """
    resolved_provider = (
        provider_name
        if provider_name is not None
        else (_read_config_value("AI_PROVIDER", "openrouter") or "openrouter")
    ).strip().lower()

    if resolved_provider in _CUSTOM_PROVIDERS:
        return _CUSTOM_PROVIDERS[resolved_provider](
            api_key=api_key,
            model=model,
            timeout_s=timeout_s,
            **kwargs,
        )

    if resolved_provider == "openrouter":
        resolved_key = (
            api_key if api_key is not None else (_read_config_value("AI_API_KEY", "") or "")
        ).strip()
        if not resolved_key:
            raise AINotConfiguredError(
                "El servicio de IA no está configurado: falta la variable AI_API_KEY en .env."
            )

        resolved_model = (
            model
            if model is not None
            else (_read_config_value("AI_MODEL", DEFAULT_OPENROUTER_MODEL) or DEFAULT_OPENROUTER_MODEL)
        ).strip()

        raw_timeout = (
            str(timeout_s)
            if timeout_s is not None
            else (_read_config_value("AI_TIMEOUT_S", str(DEFAULT_TIMEOUT_S)) or str(DEFAULT_TIMEOUT_S))
        )
        try:
            resolved_timeout = float(raw_timeout)
        except ValueError as exc:
            raise AINotConfiguredError(f"AI_TIMEOUT_S inválido: '{raw_timeout}'.") from exc

        resolved_base_url = (
            base_url
            if base_url is not None
            else (
                _read_config_value("AI_BASE_URL", DEFAULT_OPENROUTER_BASE_URL)
                or DEFAULT_OPENROUTER_BASE_URL
            )
        ).strip()

        raw_temp = (
            str(temperature)
            if temperature is not None
            else (_read_config_value("AI_TEMPERATURE", str(DEFAULT_TEMPERATURE)) or str(DEFAULT_TEMPERATURE))
        )
        try:
            resolved_temp = float(raw_temp)
        except ValueError as exc:
            raise AINotConfiguredError(f"AI_TEMPERATURE inválido: '{raw_temp}'.") from exc

        site_url = _read_config_value("AI_SITE_URL") or None
        app_name = _read_config_value("AI_APP_NAME", "PrettyDocs") or "PrettyDocs"

        return OpenRouterProvider(
            api_key=resolved_key,
            model=resolved_model,
            timeout_s=resolved_timeout,
            base_url=resolved_base_url,
            temperature=resolved_temp,
            site_url=site_url,
            app_name=app_name,
            **kwargs,
        )

    raise AINotConfiguredError(
        f"Proveedor de IA no soportado: '{resolved_provider}'. "
        "Configura AI_PROVIDER=openrouter en .env."
    )
