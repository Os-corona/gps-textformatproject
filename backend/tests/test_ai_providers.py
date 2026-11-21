"""
Pruebas unitarias (con mocks, sin red) y prueba real (@pytest.mark.live) para
la capa de proveedores de IA (S3T16 / S3T8).
"""

from __future__ import annotations

import json
import logging
from types import SimpleNamespace
from unittest.mock import MagicMock

import httpx2 as httpx
import openai
import pytest

from ai_engine.providers import (
    AI_NOT_CONFIGURED,
    AINotConfiguredError,
    InvalidModelOutputError,
    LLMProvider,
    OpenRouterProvider,
    ProviderAuthError,
    ProviderRateLimitError,
    ProviderResult,
    ProviderUnavailableError,
    TokenUsage,
    get_provider,
)
from common.document_schema import AIChunkInput, AIChunkOutput, Hints, Run, SourceBlock


# ---------------------------------------------------------------------------
# Helpers de fixtures y respuestas simuladas del SDK
# ---------------------------------------------------------------------------
def _make_sample_chunk(secret_text: str = "1. RESUMEN EJECUTIVO") -> AIChunkInput:
    return AIChunkInput(
        chunk_id="chunk-001",
        document_id=42,
        blocks=[
            SourceBlock(
                id="b1",
                type="paragraph",
                text=secret_text,
                runs=[Run(text=secret_text, bold=True)],
                hints=Hints(all_bold=True, size_ratio=1.45, words=3, ends_with_period=False),
            ),
            SourceBlock(
                id="b2",
                type="paragraph",
                text="• Ventas: incremento del 15%.",
                runs=[Run(text="• Ventas: incremento del 15%.")],
                hints=Hints(starts_with_glyph=True, indent_level=0),
            ),
            SourceBlock(
                id="b3",
                type="keep",
            ),
        ],
    )


def _valid_output_payload(chunk_id: str = "chunk-001", heading_text: str = "1. RESUMEN EJECUTIVO") -> dict:
    return {
        "schema_version": "di.v1",
        "chunk_id": chunk_id,
        "blocks": [
            {
                "type": "heading",
                "level": 1,
                "src": ["b1"],
                "runs": [{"text": heading_text}],
            },
            {
                "type": "list_item",
                "ordered": False,
                "level": 0,
                "src": ["b2"],
                "runs": [
                    {"text": "Ventas:", "bold": True},
                    {"text": " incremento del 15%."},
                ],
            },
            {
                "type": "keep",
                "id": "b3",
                "src": ["b3"],
            },
        ],
    }


def _mock_completion_response(
    content: str | None,
    *,
    prompt_tokens: int = 120,
    completion_tokens: int = 85,
    total_tokens: int = 205,
    model: str = "google/gemini-2.0-flash-001",
):
    return SimpleNamespace(
        model=model,
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
        usage=SimpleNamespace(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
        ),
    )


def _make_httpx_response(status_code: int) -> httpx.Response:
    req = httpx.Request("POST", "https://openrouter.ai/api/v1/chat/completions")
    return httpx.Response(status_code=status_code, request=req)


def _make_mock_client(side_effect=None, return_value=None) -> MagicMock:
    client = MagicMock()
    if side_effect is not None:
        client.chat.completions.create.side_effect = side_effect
    else:
        client.chat.completions.create.return_value = return_value
    return client


# ---------------------------------------------------------------------------
# 1. Pruebas de registry.get_provider()
# ---------------------------------------------------------------------------
class TestProviderRegistry:
    def test_get_provider_reads_env_vars(self, monkeypatch):
        monkeypatch.setenv("AI_PROVIDER", "openrouter")
        monkeypatch.setenv("AI_API_KEY", "sk-or-v1-test-key")
        monkeypatch.setenv("AI_MODEL", "openai/gpt-4o-mini")
        monkeypatch.setenv("AI_TIMEOUT_S", "45")
        monkeypatch.setenv("AI_TEMPERATURE", "0.15")

        provider = get_provider(client=_make_mock_client())
        assert isinstance(provider, LLMProvider)
        assert isinstance(provider, OpenRouterProvider)
        assert provider.model == "openai/gpt-4o-mini"
        assert provider.timeout_s == 45.0
        assert provider.temperature == 0.15

    def test_get_provider_raises_ai_not_configured_when_key_missing(self, monkeypatch):
        monkeypatch.setenv("AI_PROVIDER", "openrouter")
        monkeypatch.setenv("AI_API_KEY", "")

        with pytest.raises(AINotConfiguredError) as exc_info:
            get_provider()

        assert exc_info.value.error_code == "AI_NOT_CONFIGURED"
        assert issubclass(AI_NOT_CONFIGURED, AINotConfiguredError)

    def test_get_provider_raises_ai_not_configured_when_key_whitespace(self, monkeypatch):
        monkeypatch.setenv("AI_PROVIDER", "openrouter")
        monkeypatch.setenv("AI_API_KEY", "   ")

        with pytest.raises(AINotConfiguredError) as exc_info:
            get_provider()
        assert exc_info.value.error_code == "AI_NOT_CONFIGURED"

    def test_get_provider_raises_ai_not_configured_for_unknown_provider(self, monkeypatch):
        monkeypatch.setenv("AI_PROVIDER", "proveedor_desconocido")
        monkeypatch.setenv("AI_API_KEY", "sk-or-v1-test-key")

        with pytest.raises(AINotConfiguredError) as exc_info:
            get_provider()
        assert exc_info.value.error_code == "AI_NOT_CONFIGURED"

    def test_get_provider_invalid_timeout_raises_ai_not_configured(self, monkeypatch):
        monkeypatch.setenv("AI_PROVIDER", "openrouter")
        monkeypatch.setenv("AI_API_KEY", "sk-or-v1-test-key")
        monkeypatch.setenv("AI_TIMEOUT_S", "no-es-numero")

        with pytest.raises(AINotConfiguredError) as exc_info:
            get_provider()
        assert exc_info.value.error_code == "AI_NOT_CONFIGURED"


# ---------------------------------------------------------------------------
# 2. Pruebas de OpenRouterProvider (esquema, temperatura, Pydantic, reintentos)
# ---------------------------------------------------------------------------
class TestOpenRouterProvider:
    def test_temperature_out_of_range_rejected(self):
        with pytest.raises(ValueError, match="temperature"):
            OpenRouterProvider(api_key="sk-or-v1-test", temperature=0.5, client=_make_mock_client())

        with pytest.raises(ValueError, match="temperature"):
            OpenRouterProvider(api_key="sk-or-v1-test", temperature=-0.1, client=_make_mock_client())

    def test_structure_success_parses_pydantic_and_tracks_usage(self):
        payload = _valid_output_payload()
        mock_client = _make_mock_client(
            return_value=_mock_completion_response(
                json.dumps(payload),
                prompt_tokens=150,
                completion_tokens=90,
                total_tokens=240,
                model="google/gemini-2.0-flash-001",
            )
        )
        provider = OpenRouterProvider(
            api_key="sk-or-v1-test",
            model="google/gemini-2.0-flash-001",
            temperature=0.1,
            client=mock_client,
        )

        result = provider.structure(_make_sample_chunk())

        assert isinstance(result, ProviderResult)
        assert isinstance(result.output, AIChunkOutput)
        assert isinstance(result.usage, TokenUsage)
        assert result.output.chunk_id == "chunk-001"
        assert len(result.output.blocks) == 3
        assert result.output.blocks[0].type == "heading"
        assert result.output.blocks[1].type == "list_item"
        assert result.output.blocks[2].type == "keep"
        assert result.usage.input_tokens == 150
        assert result.usage.output_tokens == 90
        assert result.usage.total_tokens == 240
        assert result.usage.attempts == 1
        assert result.usage.provider == "openrouter"

        # Verificar que se envió JSON Schema y temperatura <= 0.2
        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        assert call_kwargs["model"] == "google/gemini-2.0-flash-001"
        assert 0.0 <= call_kwargs["temperature"] <= 0.2
        assert call_kwargs["response_format"]["type"] == "json_schema"
        assert call_kwargs["response_format"]["json_schema"]["name"] == "aichunk_output"
        assert "properties" in call_kwargs["response_format"]["json_schema"]["schema"]

    def test_structure_accepts_markdown_fenced_json(self):
        fenced = f"```json\n{json.dumps(_valid_output_payload())}\n```"
        mock_client = _make_mock_client(return_value=_mock_completion_response(fenced))
        provider = OpenRouterProvider(api_key="sk-or-v1-test", client=mock_client)

        result = provider.structure(_make_sample_chunk())
        assert result.output.chunk_id == "chunk-001"

    @pytest.mark.parametrize(
        "bad_content",
        [
            "",
            "   ",
            None,
            "esto no es json",
            '["no es un objeto"]',
            json.dumps({"schema_version": "di.v1", "blocks": []}),  # falta chunk_id
            json.dumps(
                {
                    "schema_version": "di.v1",
                    "chunk_id": "chunk-001",
                    "blocks": [{"type": "heading", "level": 1, "runs": []}],  # runs vacío
                }
            ),
            json.dumps(
                {
                    "schema_version": "di.v1",
                    "chunk_id": "chunk-001",
                    "blocks": [{"type": "tipo_inexistente", "runs": [{"text": "hola"}]}],
                }
            ),
        ],
    )
    def test_invalid_model_output_raises_error(self, bad_content):
        mock_client = _make_mock_client(return_value=_mock_completion_response(bad_content))
        provider = OpenRouterProvider(api_key="sk-or-v1-test", client=mock_client)

        with pytest.raises(InvalidModelOutputError):
            provider.structure(_make_sample_chunk())

    def test_auth_error_does_not_retry(self):
        auth_exc = openai.AuthenticationError(
            "Invalid API key",
            response=_make_httpx_response(401),
            body=None,
        )
        mock_client = _make_mock_client(side_effect=auth_exc)
        sleeps: list[float] = []
        provider = OpenRouterProvider(
            api_key="sk-or-v1-invalid",
            client=mock_client,
            sleep_fn=sleeps.append,
        )

        with pytest.raises(ProviderAuthError):
            provider.structure(_make_sample_chunk())

        assert mock_client.chat.completions.create.call_count == 1
        assert sleeps == []

    def test_rate_limit_retries_3_times_with_exponential_backoff(self):
        rate_exc = openai.RateLimitError(
            "Rate limit exceeded",
            response=_make_httpx_response(429),
            body=None,
        )
        mock_client = _make_mock_client(side_effect=rate_exc)
        sleeps: list[float] = []
        provider = OpenRouterProvider(
            api_key="sk-or-v1-test",
            backoff_base_s=1.0,
            client=mock_client,
            sleep_fn=sleeps.append,
        )

        with pytest.raises(ProviderRateLimitError) as exc_info:
            provider.structure(_make_sample_chunk())

        assert exc_info.value.error_code == "AI_RATE_LIMIT"
        assert mock_client.chat.completions.create.call_count == 3
        assert sleeps == [1.0, 2.0]

    def test_server_5xx_retries_3_times_then_raises_unavailable(self):
        server_exc = openai.InternalServerError(
            "Upstream 503",
            response=_make_httpx_response(503),
            body=None,
        )
        mock_client = _make_mock_client(side_effect=server_exc)
        sleeps: list[float] = []
        provider = OpenRouterProvider(
            api_key="sk-or-v1-test",
            backoff_base_s=0.5,
            client=mock_client,
            sleep_fn=sleeps.append,
        )

        with pytest.raises(ProviderUnavailableError) as exc_info:
            provider.structure(_make_sample_chunk())

        assert exc_info.value.error_code == "AI_UNAVAILABLE"
        assert mock_client.chat.completions.create.call_count == 3
        assert sleeps == [0.5, 1.0]

    def test_transient_5xx_recovers_on_second_attempt(self):
        server_exc = openai.InternalServerError(
            "Temporary 502",
            response=_make_httpx_response(502),
            body=None,
        )
        ok_resp = _mock_completion_response(json.dumps(_valid_output_payload()))
        mock_client = _make_mock_client(side_effect=[server_exc, ok_resp])
        sleeps: list[float] = []
        provider = OpenRouterProvider(
            api_key="sk-or-v1-test",
            backoff_base_s=1.0,
            client=mock_client,
            sleep_fn=sleeps.append,
        )

        result = provider.structure(_make_sample_chunk())

        assert result.usage.attempts == 2
        assert mock_client.chat.completions.create.call_count == 2
        assert sleeps == [1.0]

    def test_logs_never_leak_api_key_or_document_text(self, caplog):
        secret_key = "sk-or-v1-SUPER-SECRET-KEY-99999"
        secret_doc_text = "CONFIDENCIAL_NO_LOGUEAR_XYZ_777"
        chunk = _make_sample_chunk(secret_text=secret_doc_text)

        # Caso 1: éxito
        ok_client = _make_mock_client(
            return_value=_mock_completion_response(
                json.dumps(_valid_output_payload(heading_text=secret_doc_text))
            )
        )
        provider_ok = OpenRouterProvider(api_key=secret_key, client=ok_client)

        # Caso 2: error 401
        auth_exc = openai.AuthenticationError(
            f"Bad key {secret_key} for text {secret_doc_text}",
            response=_make_httpx_response(401),
            body=None,
        )
        provider_err = OpenRouterProvider(
            api_key=secret_key,
            client=_make_mock_client(side_effect=auth_exc),
        )

        # Caso 3: salida inválida que incluye el texto secreto
        bad_client = _make_mock_client(
            return_value=_mock_completion_response(f"INVALIDO {secret_doc_text}")
        )
        provider_bad = OpenRouterProvider(api_key=secret_key, client=bad_client)

        with caplog.at_level(logging.DEBUG, logger="ai_engine"):
            provider_ok.structure(chunk)
            with pytest.raises(ProviderAuthError):
                provider_err.structure(chunk)
            with pytest.raises(InvalidModelOutputError):
                provider_bad.structure(chunk)

        full_log_text = "\n".join(record.getMessage() for record in caplog.records)
        assert secret_key not in full_log_text
        assert secret_doc_text not in full_log_text


# ---------------------------------------------------------------------------
# 3. Prueba real contra OpenRouter (excluida por defecto; correr con -m live)
# ---------------------------------------------------------------------------
@pytest.mark.live
def test_openrouter_live_structure():
    """
    Prueba de integración real contra OpenRouter usando AI_API_KEY y AI_MODEL de backend/.env.
    Ejecutar manualmente con:
        pytest tests/test_ai_providers.py -m live -s
    """
    try:
        provider = get_provider()
    except AINotConfiguredError:
        pytest.skip("AI_API_KEY no configurada en backend/.env; omitiendo prueba live.")

    chunk = _make_sample_chunk()
    result = provider.structure(chunk)

    assert isinstance(result, ProviderResult)
    assert isinstance(result.output, AIChunkOutput)
    assert result.output.chunk_id == chunk.chunk_id
    assert len(result.output.blocks) >= 1
    assert result.usage.input_tokens > 0
    assert result.usage.output_tokens > 0

    print(
        f"\n[LIVE OpenRouter OK] model={result.usage.model} "
        f"in={result.usage.input_tokens} out={result.usage.output_tokens} "
        f"total={result.usage.total_tokens} blocks={len(result.output.blocks)}"
    )
    print(result.output.model_dump_json(indent=2))
