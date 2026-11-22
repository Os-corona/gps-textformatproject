"""
Motor de Inteligencia Artificial (ai_engine) de PrettyDocs.
"""

from .chunker import (
    AI_MAX_CHUNK_CHARS,
    AI_MAX_DOC_CHARS,
    BlockTooLargeForAI,
    DocumentTooLargeForAI,
    chunk_document,
    ensure_within_limit,
)
from .prompts import (
    FEW_SHOT_EXAMPLES,
    PROMPT_VERSION,
    SYSTEM_PROMPT,
    build_glyph_list_example,
    build_messages,
    build_system_prompt,
    build_user_prompt,
    get_few_shot_examples,
)

__all__ = [
    "AI_MAX_CHUNK_CHARS",
    "AI_MAX_DOC_CHARS",
    "BlockTooLargeForAI",
    "DocumentTooLargeForAI",
    "FEW_SHOT_EXAMPLES",
    "PROMPT_VERSION",
    "SYSTEM_PROMPT",
    "build_glyph_list_example",
    "build_messages",
    "build_system_prompt",
    "build_user_prompt",
    "chunk_document",
    "ensure_within_limit",
    "get_few_shot_examples",
]
