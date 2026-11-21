"""Offline provider and deterministic error simulation for integration tests."""
from ai_engine.heuristic import structure
from .base import (LLMProvider, ProviderResult, TokenUsage, ProviderAuthError,
                   ProviderRateLimitError, ProviderUnavailableError, InvalidModelOutputError)


class FakeProvider(LLMProvider):
    name = 'fake'

    def __init__(self, *, error=None, **kwargs):
        """error: auth, rate_limit, timeout o invalid_output; None produce salida normal."""
        self.error = error
        if error not in (None, 'auth', 'rate_limit', 'timeout', 'invalid_output'):
            raise ValueError(f'Unknown fake provider error: {error}')

    def structure(self, chunk_input, *, feedback=None):
        errors = {'auth': ProviderAuthError, 'rate_limit': ProviderRateLimitError,
                  'timeout': ProviderUnavailableError, 'invalid_output': InvalidModelOutputError}
        if self.error:
            raise errors[self.error](f'Simulated {self.error} error')
        return ProviderResult(output=structure(chunk_input), usage=TokenUsage(provider=self.name))
