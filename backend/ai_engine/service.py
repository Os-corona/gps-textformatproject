"""Chunked AI structuring with one integrity retry and deterministic fallback."""
from __future__ import annotations

import json
from collections import Counter
from dataclasses import asdict
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
    usage: dict[str, Any] = Field(default_factory=lambda: {
        "input_tokens": 0, "output_tokens": 0, "total_tokens": 0, "calls": 0,
        "attempts": 0, "models": [], "providers": [],
    })


def _strip_excess_bold(output: AIChunkOutput, offending_refs: set[str]) -> AIChunkOutput:
    """Clear added bold flags only on blocks flagged with BOLD_RATIO so valid AI structure is preserved."""
    cleaned = output.model_copy(deep=True)
    for block in cleaned.blocks:
        refs = set(getattr(block, "src", None) or [])
        if offending_refs and not (refs & offending_refs):
            continue
        if getattr(block, "runs", None):
            for run in block.runs:
                if run.bold:
                    run.bold = None
        if getattr(block, "rows", None):
            for row in block.rows:
                for cell in row:
                    if cell.runs:
                        for run in cell.runs:
                            if run.bold:
                                run.bold = None
    return cleaned


def structure_document(di, options=None, provider=None, *, on_progress=None) -> StructureResult:
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

    def progress(stage, done):
        if on_progress is not None:
            on_progress(stage, done, len(chunks))

    progress("structuring", 0)
    provider_error = None
    if provider is None and chunks:
        try:
            provider = get_provider()
        except (AINotConfiguredError, ProviderAuthError):
            raise
        except ProviderError as exc:
            provider_error = exc

    for index, chunk in enumerate(chunks):
        chunk.metadata["ai_options"] = options
        feedback, accepted = None, None
        max_attempts = 1 if provider_error is not None else 2
        for attempt in range(max_attempts):
            if attempt:
                result.summary["chunks_retried"] += 1
            try:
                progress("structuring", index)
                if provider_error is not None:
                    raise provider_error
                result.usage["calls"] += 1
                response = provider.structure(chunk.model_copy(deep=True), feedback=feedback)
                usage = asdict(response.usage) if hasattr(response, "usage") else {}
                for name in ("input_tokens", "output_tokens", "total_tokens", "attempts"):
                    result.usage[name] += usage.get(name, 0)
                for name, destination in (("model", "models"), ("provider", "providers")):
                    value = usage.get(name)
                    if value and value not in result.usage[destination]:
                        result.usage[destination].append(value)
                output = AIChunkOutput.model_validate(response.output)
                progress("validating", index)
                report = validate_chunk(chunk.blocks, output.blocks)
                if not report.ok and report.violations and all(v.type == "BOLD_RATIO" for v in report.violations):
                    offending_refs = {ref for v in report.violations for ref in v.src}
                    sanitized = _strip_excess_bold(output, offending_refs)
                    recheck = validate_chunk(chunk.blocks, sanitized.blocks)
                    if recheck.ok:
                        output = sanitized
                        report = recheck
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
                    }], errors=[str(exc)], metadata={
                        "chunk_id": chunk.chunk_id,
                        "error_code": getattr(exc, "error_code", "AI_UNAVAILABLE"),
                    },
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
        progress("validating", index + 1)

    result.summary["blocks_by_type"] = dict(Counter(b.type for b in result.blocks))
    result.summary["generated_elements"] = sum(
        int(getattr(b, "generated", False))
        + sum(int(c.generated) for row in getattr(b, "rows", []) for c in row)
        for b in result.blocks
    )
    return result
