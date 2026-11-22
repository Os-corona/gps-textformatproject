"""Persistent AI proposal and approved-document finalization pipeline."""
from copy import deepcopy
from datetime import timedelta
from io import BytesIO

from docx import Document as DocxDocument
from django.conf import settings
from django.core.files.base import ContentFile
from django.db.models import Q
from django.utils import timezone

from ai_engine.chunker import DocumentTooLargeForAI, ensure_within_limit
from ai_engine.providers.base import (
    AINotConfiguredError,
    ProviderAuthError,
    ProviderError,
    ProviderRateLimitError,
)
from ai_engine.service import structure_document
from ai_engine.validator import _critical
from common.integrity import validate_tokens
from documents.models import ProcessingJob
from docx_engine.extractor import extract_document
from docx_engine.rebuilder import DocumentIntegrityError, _element_text, rebuild_document
from templates_engine.applier import apply_template


class InvalidJobState(ValueError):
    pass


def mark_job_error(job_id, exc):
    """Persist only a typed code and a safe message; no provider/document details."""
    if isinstance(exc, (ProviderAuthError, AINotConfiguredError)):
        code, message = "AI_NOT_CONFIGURED", "El proveedor de IA no está configurado o rechazó la autenticación."
    elif isinstance(exc, ProviderRateLimitError):
        code, message = "AI_RATE_LIMIT", "Se superó el límite de peticiones del proveedor de IA. Intenta de nuevo en unos momentos."
    elif isinstance(exc, DocumentTooLargeForAI):
        code, message = exc.error_code, "El documento o un bloque excede el límite permitido para IA."
    elif isinstance(exc, ProviderError):
        code, message = getattr(exc, "error_code", "AI_UNAVAILABLE"), "El proveedor de IA no está disponible."
    else:
        code, message = "PROCESSING_ERROR", "No se pudo procesar el documento."
    ProcessingJob.objects.filter(pk=job_id, status__in=("pending", "processing")).update(
        status="error", error_code=code, error_message=message, finished_at=timezone.now(),
    )


def recover_stale_jobs(*, max_age_minutes=10) -> int:
    """Mark jobs stuck in processing after a server restart as error so documents can be retried."""
    cutoff = timezone.now() - timedelta(minutes=max_age_minutes)
    return ProcessingJob.objects.filter(status="processing").filter(
        Q(started_at__lt=cutoff) | Q(started_at__isnull=True, created_at__lt=cutoff)
    ).update(
        status="error",
        error_code="PROCESSING_ERROR",
        error_message="El procesamiento anterior fue interrumpido. Intenta de nuevo.",
        finished_at=timezone.now(),
    )


def run_ai_structuring(job_id):
    """Claim a queued job atomically, extract once and save its proposal for review."""
    claimed = ProcessingJob.objects.filter(pk=job_id).filter(
        Q(status="pending") | Q(status="processing", progress_stage="queued")
    ).update(
        status="processing", progress_stage="extracting", progress_done=0, progress_total=0,
        started_at=timezone.now(), finished_at=None, error_code=None, error_message=None,
        structure_original=None, structure_proposed=None, ai_suggestions=None,
        ai_summary=None, ai_usage=None, result_file=None,
    )
    if not claimed:
        return None
    try:
        job = ProcessingJob.objects.select_related("document").get(pk=job_id)
        with job.document.original_file.open("rb") as original:
            di = extract_document(BytesIO(original.read()))
        ensure_within_limit(di, max_chars=getattr(settings, "AI_MAX_DOC_CHARS", 60000))
        ProcessingJob.objects.filter(pk=job_id).update(structure_original=di.model_dump(mode="json", exclude_none=True))

        def progress(stage, done, total):
            ProcessingJob.objects.filter(pk=job_id, status="processing").update(
                progress_stage=stage, progress_done=done, progress_total=total,
            )

        result = structure_document(di, job.config.get("ai") or {}, on_progress=progress)
        # S3T18 can fall back on provider failures, but authentication failures must
        # remain visible as configuration errors rather than masquerading as success.
        if any((r.metadata or {}).get("error_code") == "AI_NOT_CONFIGURED" for r in result.reports):
            raise AINotConfiguredError("Autenticación de IA rechazada.")
        summary = dict(result.summary)
        summary["fallback_only"] = summary["chunks_total"] > 0 and summary["chunks_heuristic"] == summary["chunks_total"]
        summary.update({
            "chunks_fallback": summary["chunks_heuristic"],
            "headings_detected": summary["blocks_by_type"].get("heading", 0),
            "lists_detected": summary["blocks_by_type"].get("list_item", 0),
            "tables_detected": summary["blocks_by_type"].get("table", 0),
            "bold_emphasis_applied": sum(
                int(bool(run.bold)) for block in result.blocks
                for run in (getattr(block, "runs", None) or [])
            ) + sum(
                int(bool(run.bold)) for block in result.blocks
                for row in getattr(block, "rows", []) for cell in row for run in (cell.runs or [])
            ),
        })
        proposed = {"schema_version": di.schema_version, "blocks": [b.model_dump(mode="json", exclude_none=True) for b in result.blocks]}
        ProcessingJob.objects.filter(pk=job_id, status="processing").update(
            status="review", progress_stage="validating",
            progress_done=summary["chunks_total"], progress_total=summary["chunks_total"],
            structure_proposed=proposed, ai_suggestions=proposed,
            ai_summary=summary, ai_usage=result.usage,
        )
    except Exception as exc:
        mark_job_error(job_id, exc)
    return ProcessingJob.objects.get(pk=job_id)


def restore_original_blocks(original, proposed, revert_ids):
    """Restore original XML references, expanding inseparable merged source groups.

    Selecting any source of a merged table restores all its sources; a split source
    is restored once. Generated headings anchored to reverted sources are removed.
    """
    source_ids = [b["id"] for b in original["blocks"]]
    source_set = set(source_ids)
    empty_keep_ids = {
        b["id"] for b in original["blocks"]
        if b.get("type") == "keep" and b.get("keep_kind") == "empty"
    }
    if not isinstance(revert_ids, (list, tuple, set)) or any(not isinstance(sid, str) for sid in revert_ids):
        raise ValueError("revert_ids debe ser una lista de IDs de origen.")
    selected = set(revert_ids)
    if not selected <= source_set:
        raise ValueError("Hay IDs de reversión que no pertenecen al documento original.")
    blocks = deepcopy(proposed["blocks"])
    if not selected:
        return {**deepcopy(proposed), "blocks": blocks}, []
    changed = True
    while changed:
        changed = False
        for block in blocks:
            refs = set(block.get("src") or ([block["id"]] if block.get("type") == "keep" and block.get("id") else []))
            if not block.get("generated") and refs & selected and not refs <= selected:
                selected.update(refs)
                changed = True
    restored, emitted = [], set()
    for block in blocks:
        refs = set(block.get("src") or ([block["id"]] if block.get("type") == "keep" and block.get("id") else []))
        if block.get("generated") and (refs & selected or selected == source_set):
            continue
        if refs & selected:
            # Output refs retain source order; emit all merged originals at this point.
            for sid in source_ids:
                if sid in refs and sid in selected and sid not in emitted:
                    restored.append({"type": "keep", "id": sid, "src": [sid]})
                    emitted.add(sid)
        else:
            restored.append(block)
    missing = selected - emitted
    if missing - empty_keep_ids:
        raise ValueError("La propuesta no contiene todos los orígenes que se quieren restaurar.")
    return {**deepcopy(proposed), "blocks": restored}, [sid for sid in source_ids if sid in emitted]


def finalize_job(job, revert_ids):
    """Finalize an approved review; all expensive work happens outside a DB transaction."""
    job.refresh_from_db()
    if job.status != "review":
        raise InvalidJobState("Solo se puede finalizar un trabajo en revisión.")
    if (
        not isinstance(job.structure_original, dict)
        or "blocks" not in job.structure_original
        or not isinstance(job.structure_proposed, dict)
        or "blocks" not in job.structure_proposed
    ):
        raise InvalidJobState("El trabajo en revisión no contiene una propuesta válida para finalizar.")
    # Invalid user selections leave the proposal in review and do not claim the job.
    structured, reverted = restore_original_blocks(job.structure_original, job.structure_proposed, revert_ids)
    if not ProcessingJob.objects.filter(pk=job.pk, status="review").update(
        status="processing", progress_stage="building", error_code=None, error_message=None,
    ):
        raise InvalidJobState("El trabajo ya está siendo finalizado.")
    saved_name = None
    try:
        with job.document.original_file.open("rb") as original:
            rebuilt = rebuild_document(BytesIO(original.read()), structured)
        expected = _element_text(rebuilt.element.body)
        apply_template(rebuilt, job.config)
        buffer = BytesIO()
        rebuilt.save(buffer)
        buffer.seek(0)
        reopened = DocxDocument(buffer)
        actual = _element_text(reopened.element.body)
        report = validate_tokens(expected, actual)
        if not report.ok or _critical(expected) != _critical(actual):
            raise DocumentIntegrityError(report)
        buffer.seek(0)
        job.result_file.save(f"result_{job.pk}.docx", ContentFile(buffer.read()), save=False)
        saved_name = job.result_file.name
        applied_blocks = structured.get("blocks") or []
        headings_applied = sum(1 for b in applied_blocks if b.get("type") == "heading")
        lists_applied = sum(1 for b in applied_blocks if b.get("type") == "list_item")
        tables_applied = sum(1 for b in applied_blocks if b.get("type") == "table")
        summary = {
            **(job.ai_summary or {}),
            "headings_applied": headings_applied,
            "lists_applied": lists_applied,
            "tables_applied": tables_applied,
            "reverted_blocks_count": len(reverted),
            "reverted_source_ids": reverted,
        }
        completed = ProcessingJob.objects.filter(pk=job.pk, status="processing", progress_stage="building").update(
            status="done", progress_stage="building", progress_done=job.progress_total,
            ai_summary=summary, result_file=saved_name, finished_at=timezone.now(),
            error_code=None, error_message=None,
        )
        if not completed:
            raise InvalidJobState("El trabajo dejó de estar en finalización.")
    except Exception as exc:
        if saved_name:
            try:
                job.result_file.storage.delete(saved_name)
            except Exception:
                # Cleanup failure must not leave a job stuck in processing.
                pass
        mark_job_error(job.pk, exc)
    job.refresh_from_db()
    return job
