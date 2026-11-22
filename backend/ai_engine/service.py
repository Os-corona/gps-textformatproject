"""Chunked AI structuring with one integrity retry and deterministic fallback."""
from __future__ import annotations

import json
from collections import Counter
from typing import Any

from django.conf import settings
from pydantic import BaseModel, Field, ValidationError

from common.document_schema import AIChunkOutput, DocumentIntermediate, IntegrityReport, IntegrityViolation, OutBlock
from . import heuristic
from .chunker import AI_MAX_CHUNK_CHARS, AI_MAX_DOC_CHARS, chunk_document
from .providers.base import AINotConfiguredError, ProviderAuthError, ProviderError
from .providers.registry import get_provider
from .validator import validate_chunk


class StructureResult(BaseModel):
    blocks: list[OutBlock] = Field(default_factory=list)
    chunks: list[AIChunkOutput] = Field(default_factory=list)
    reports: list[IntegrityReport] = Field(default_factory=list)
    summary: dict[str, Any] = Field(default_factory=dict)


def structure_document(di, options=None, provider=None) -> StructureResult:
    """Return accepted/fallback blocks, attempt reports and counts for the whole DI.

    Guardrail and size settings are application configuration, never document options.
    Provider transport retries remain the responsibility of the provider itself.
    """
    if not isinstance(di, DocumentIntermediate):
        di = DocumentIntermediate.model_validate(di)
    options = dict(options or {})
    chunk_limit = getattr(settings, "AI_MAX_CHUNK_CHARS", AI_MAX_CHUNK_CHARS) if settings.configured else AI_MAX_CHUNK_CHARS
    doc_limit = getattr(settings, "AI_MAX_DOC_CHARS", AI_MAX_DOC_CHARS) if settings.configured else AI_MAX_DOC_CHARS
    chunks = chunk_document(di, max_chunk_chars=chunk_limit, max_doc_chars=doc_limit)
    result = StructureResult(summary={
        "chunks_total": len(chunks), "chunks_ai": 0, "chunks_retried": 0,
        "chunks_heuristic": 0, "blocks_by_type": {}, "generated_elements": 0,
    })
    provider_error = None
    if provider is None and chunks:
        try:
            provider = get_provider()
        except (AINotConfiguredError, ProviderAuthError):
            raise
        except ProviderError as exc:
            provider_error = exc

    for chunk in chunks:
        chunk.metadata["ai_options"] = options
        feedback, accepted = None, None
        max_attempts = 1 if provider_error is not None else 2
        for attempt in range(max_attempts):
            if attempt:
                result.summary["chunks_retried"] += 1
            try:
                if provider_error is not None:
                    raise provider_error
                response = provider.structure(chunk.model_copy(deep=True), feedback=feedback)
                output = AIChunkOutput.model_validate(response.output)
                report = validate_chunk(chunk.blocks, output.blocks)
                if output.chunk_id != chunk.chunk_id:
                    report.is_valid = False
                    report.violations.append(IntegrityViolation(
                        type="CHUNK_ID", src=[b.id for b in chunk.blocks],
                        message="El proveedor devolvió un chunk_id distinto.",
                    ))
                    report.errors.append("El proveedor devolvió un chunk_id distinto.")
            except (AINotConfiguredError, ProviderAuthError):
                raise
            except (ProviderError, ValidationError) as exc:
                report = IntegrityReport(
                    is_valid=False, violations=[{
                        "type": "PROVIDER_OUTPUT", "src": [b.id for b in chunk.blocks],
                        "message": str(exc),
                    }], errors=[str(exc)], metadata={"chunk_id": chunk.chunk_id},
                )
            report.metadata = {**(report.metadata or {}), "chunk_id": chunk.chunk_id, "attempt": attempt + 1}
            result.reports.append(report)
            if report.ok:
                accepted = output
                result.summary["chunks_ai"] += 1
                break
            feedback = json.dumps([v.model_dump() for v in report.violations], ensure_ascii=False)
        if accepted is None:
            accepted = heuristic.structure(chunk)
            result.summary["chunks_heuristic"] += 1
        result.chunks.append(accepted)
        result.blocks.extend(accepted.blocks)

    result.summary["blocks_by_type"] = dict(Counter(b.type for b in result.blocks))
    result.summary["generated_elements"] = sum(
        int(getattr(b, "generated", False))
        + sum(int(c.generated) for row in getattr(b, "rows", []) for c in row)
        for b in result.blocks
    )
    return result
