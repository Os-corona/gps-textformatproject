"""
Motor de Inteligencia Artificial (ai_engine) de PrettyDocs.
"""

from .chunker import (
    AI_MAX_CHUNK_CHARS,
    AI_MAX_DOC_CHARS,
    DocumentTooLargeForAI,
    chunk_document,
    ensure_within_limit,
)
from .prompts import (
    FEW_SHOT_EXAMPLES,
    PROMPT_VERSION,
    SYSTEM_PROMPT,
    build_messages,
    build_system_prompt,
    build_user_prompt,
)

__all__ = [
    "AI_MAX_CHUNK_CHARS",
    "AI_MAX_DOC_CHARS",
    "DocumentTooLargeForAI",
    "FEW_SHOT_EXAMPLES",
    "PROMPT_VERSION",
    "SYSTEM_PROMPT",
    "build_messages",
    "build_system_prompt",
    "build_user_prompt",
    "chunk_document",
    "ensure_within_limit",
]
