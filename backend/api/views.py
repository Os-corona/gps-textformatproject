from copy import deepcopy
import io
import os
import re
from collections.abc import Mapping

from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.http import FileResponse
from django.utils import timezone
from docx import Document as DocxDocument
from pydantic import ValidationError
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from documents.models import Document, ProcessingJob
from docx_engine.extractor import extract_structure
from orchestrator.ai_pipeline import InvalidJobState, finalize_job, mark_job_error
from orchestrator.pipeline import PIPELINE
from orchestrator.runner import enqueue
from templates_engine.config import TemplateConfig, list_presets, load_preset
from .serializers import DocumentUploadSerializer

_PRESET_ID_RE = re.compile(r"^[a-zA-Z0-9_-]+$")


@api_view(['POST'])
@permission_classes([AllowAny])
def extract_text_view(request):
    if 'file' not in request.FILES:
        return Response({"error": "No se proporcionó ningún archivo."}, status=status.HTTP_400_BAD_REQUEST)

    uploaded_file = request.FILES['file']

    if not uploaded_file.name.endswith('.docx'):
        return Response({"error": "El archivo debe ser un documento .docx."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        extracted_data = extract_structure(uploaded_file)
        return Response({
            'filename': uploaded_file.name,
            'total_blocks': len(extracted_data),
            'blocks': extracted_data
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({"error": f'Error al procesar el documento: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
def upload_document_view(request):
    serializer = DocumentUploadSerializer(data=request.data)
    
    if not serializer.is_valid():
        file_errors = serializer.errors.get('file', [])
        
        if file_errors:
            error_detail = file_errors[0]
            code = getattr(error_detail, 'code', 'INVALID_FILE')
            if code not in ['INVALID_FILE', 'FILE_TOO_LARGE']:
                code = 'INVALID_FILE'
            message = str(error_detail)
        else:
            code = 'INVALID_FILE'
            message = 'Error de validación desconocido.'
            
        return Response({"error": code, "message": message}, status=status.HTTP_400_BAD_REQUEST)
        
    uploaded_file = serializer.validated_data['file']
    
    dev_user, created = User.objects.get_or_create(username="dev_user", defaults={"email": "dev@test.com"})
    
    document = Document.objects.create(
        user=dev_user,
        original_file=uploaded_file,
        original_name=uploaded_file.name,
        size_bytes=uploaded_file.size
    )
    
    job = ProcessingJob.objects.create(
        document=document,
        status='pending'
    )
    
    return Response({
        "document_id": document.id,
        "job_id": job.id,
        "status": job.status,
        "original_name": document.original_name,
        "size_bytes": document.size_bytes,
        "uploaded_at": document.uploaded_at,
    }, status=status.HTTP_201_CREATED)


def _run_template_only_formatting(document: Document, job: ProcessingJob) -> None:
    """Ejecuta el formateo visual clásico (Sprint 2) in-place sobre una copia en memoria del original."""
    with document.original_file.open('rb') as orig_fh:
        doc_obj = DocxDocument(io.BytesIO(orig_fh.read()))

    for step in PIPELINE:
        doc_obj = step(doc_obj, job)

    temp_io = io.BytesIO()
    doc_obj.save(temp_io)
    temp_io.seek(0)

    try:
        DocxDocument(temp_io)
        temp_io.seek(0)
    except Exception as exc:
        raise RuntimeError("El documento resultante quedó corrupto tras el formateo.") from exc

    filename = f"result_{job.id}.docx"
    job.result_file.save(filename, ContentFile(temp_io.read()))


@api_view(['POST'])
@permission_classes([AllowAny])
def format_document_view(request, id):
    try:
        document = Document.objects.get(id=id)
    except Document.DoesNotExist:
        return Response({"error": "NOT_FOUND", "message": "El documento no existe."}, status=status.HTTP_404_NOT_FOUND)
    
    job = ProcessingJob.objects.filter(document=document).last()
    if not job:
        return Response({"error": "JOB_NOT_FOUND", "message": "Job de procesamiento no encontrado."}, status=status.HTTP_404_NOT_FOUND)

    if not isinstance(request.data, Mapping):
        return Response(
            {"error": "INVALID_CONFIG", "message": "El cuerpo de la solicitud debe ser un objeto JSON válido."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    data = dict(request.data)
    preset_id = data.pop('preset_id', None)
    if preset_id is not None and not isinstance(preset_id, str):
        return Response(
            {"error": "INVALID_CONFIG", "message": "El campo 'preset_id' debe ser una cadena de texto o null."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if isinstance(preset_id, str):
        preset_id = preset_id.strip() or None
        if preset_id and not _PRESET_ID_RE.match(preset_id):
            return Response(
                {"error": "INVALID_CONFIG", "message": f"El preset '{preset_id}' no existe."},
                status=status.HTTP_400_BAD_REQUEST,
            )

    if "use_ai" in data and not isinstance(data["use_ai"], bool):
        return Response(
            {"error": "INVALID_CONFIG", "message": "El campo 'use_ai' debe ser un valor booleano."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        if preset_id:
            preset_config = load_preset(preset_id)
            config_dict = preset_config.model_dump()
            config_dict.update(data)
            config = TemplateConfig(**config_dict)
        else:
            config = TemplateConfig(**data)
    except ValidationError as e:
        clean_errors = [{k: (str(v) if k == 'ctx' else v) for k, v in err.items()} for err in e.errors()]
        return Response({"error": "INVALID_CONFIG", "message": clean_errors}, status=status.HTTP_400_BAD_REQUEST)
    except FileNotFoundError:
        return Response({"error": "INVALID_CONFIG", "message": f"El preset '{preset_id}' no existe."}, status=status.HTTP_400_BAD_REQUEST)

    resolved_config = config.model_dump()
    resolved_config["preset_id"] = preset_id
    resolved_config["margins_cm"] = {
        "top": config.margin_top,
        "bottom": config.margin_bottom,
        "left": config.margin_left,
        "right": config.margin_right,
    }
    resolved_config["font_family"] = config.font_name
    resolved_config["font_size_pt"] = config.font_size
    resolved_config["heading_sizes_pt"] = config.heading_sizes

    job.config = resolved_config
    job.use_ai = config.use_ai
    job.status = 'processing'
    job.error_message = None
    job.started_at = timezone.now()
    claimed = ProcessingJob.objects.filter(pk=job.pk).exclude(status="processing").update(
        config=job.config, use_ai=job.use_ai, status="processing", started_at=job.started_at,
        finished_at=None, error_code=None, error_message=None, result_file=None,
        progress_stage="queued" if job.use_ai else "building", progress_done=0,
        progress_total=0 if job.use_ai else 1,
        ai_summary=None, ai_usage=None, structure_original=None, structure_proposed=None, ai_suggestions=None,
    )
    if not claimed:
        return Response({"error": "INVALID_STATE", "message": "El documento ya está siendo procesado."}, status=status.HTTP_409_CONFLICT)

    if job.use_ai:
        try:
            enqueue(job.pk)
        except Exception:
            ProcessingJob.objects.filter(pk=job.pk, status="processing").update(
                status="error", error_code="PROCESSING_ERROR",
                error_message="No se pudo iniciar el procesamiento.", finished_at=timezone.now(),
            )
            return Response({"error": "PROCESSING_ERROR", "message": "No se pudo iniciar el procesamiento."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response({
            "document_id": document.id, "job_id": job.id, "status": "processing",
            "message": "Documento encolado para estructuración con IA.",
        }, status=status.HTTP_202_ACCEPTED)

    job.refresh_from_db()

    try:
        _run_template_only_formatting(document, job)

        job.status = 'done'
        job.progress_done = job.progress_total
        job.finished_at = timezone.now()
        job.save()

        return Response({
            "document_id": document.id,
            "job_id": job.id,
            "status": job.status,
            "config": job.config,
            "finished_at": job.finished_at,
        }, status=status.HTTP_200_OK)

    except Exception:
        job.status = 'error'
        job.error_code = 'PROCESSING_ERROR'
        job.error_message = 'No se pudo procesar el documento.'
        job.finished_at = timezone.now()
        job.save()
        return Response({"error": "PROCESSING_ERROR", "message": job.error_message}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def document_status_view(request, id):
    try:
        document = Document.objects.get(id=id)
        job = ProcessingJob.objects.filter(document=document).last()
        
        if not job:
            return Response({"error": "JOB_NOT_FOUND"}, status=status.HTTP_404_NOT_FOUND)
            
        return Response({
            "document_id": document.id,
            "job_id": job.id,
            "status": job.status,
            "config": job.config,
            "original_name": document.original_name,
            "size_bytes": document.size_bytes,
            "uploaded_at": document.uploaded_at,
            "use_ai": job.use_ai,
            "progress": (
                None
                if job.status in ("pending", "error") or not job.progress_stage
                else {"stage": job.progress_stage, "done": job.progress_done, "total": job.progress_total}
            ),
            "ai_summary": job.ai_summary,
            "ai_usage": job.ai_usage,
            "error_code": job.error_code,
            "error_message": job.error_message,
            "started_at": job.started_at,
            "finished_at": job.finished_at,
            "download_url": f"/api/documents/{document.id}/download/" if job.status == 'done' else None,
        }, status=status.HTTP_200_OK)
        
    except Document.DoesNotExist:
        return Response({"error": "NOT_FOUND", "message": "El documento no existe."}, status=status.HTTP_404_NOT_FOUND)


document_detail_view = document_status_view


def _build_structure_response_payload(document: Document, job: ProcessingJob) -> dict:
    """Construye el payload de GET /api/documents/{id}/structure/ conforme al contrato v1.1."""
    raw_original = deepcopy(job.structure_original or {})
    raw_proposed = deepcopy(job.structure_proposed or {})

    ai_cfg = (job.config or {}).get("ai") or {}
    doc_type = ai_cfg.get("document_type") or (job.config or {}).get("document_type") or "reporte"
    body_font_size = float(
        raw_original.get("base_font_size")
        or (job.config or {}).get("font_size_pt")
        or (job.config or {}).get("font_size")
        or 11.0
    )

    original_blocks = []
    source_order = []
    for block in raw_original.get("blocks", []):
        if not isinstance(block, dict):
            continue
        b_copy = dict(block)
        b_copy.pop("xml", None)
        original_blocks.append(b_copy)
        if isinstance(b_copy.get("id"), str):
            source_order.append(b_copy["id"])

    proposed_blocks = []
    revertible_set = set()
    for idx, block in enumerate(raw_proposed.get("blocks", []), start=1):
        if not isinstance(block, dict):
            continue
        b_copy = dict(block)
        if not b_copy.get("id"):
            b_copy["id"] = f"p{idx}"
        if b_copy.get("type") == "list_item" and "ordered" not in b_copy:
            b_copy["ordered"] = bool(b_copy.get("is_numbered", False))
        if b_copy.get("type") == "keep" and not b_copy.get("src") and b_copy.get("id"):
            b_copy["src"] = [b_copy["id"]]
        if b_copy.get("type") not in ("keep", "image"):
            for sid in b_copy.get("src") or []:
                if isinstance(sid, str):
                    revertible_set.add(sid)
        proposed_blocks.append(b_copy)

    revertible_blocks = [sid for sid in source_order if sid in revertible_set]

    base_summary = deepcopy(job.ai_summary or {})
    headings_detected = base_summary.get(
        "headings_detected",
        sum(1 for b in proposed_blocks if b.get("type") == "heading"),
    )
    lists_detected = base_summary.get(
        "lists_detected",
        sum(1 for b in proposed_blocks if b.get("type") == "list_item"),
    )
    tables_detected = base_summary.get(
        "tables_detected",
        sum(1 for b in proposed_blocks if b.get("type") == "table"),
    )
    bold_emphasis_applied = base_summary.get(
        "bold_emphasis_applied",
        sum(
            int(bool(r.get("bold")))
            for b in proposed_blocks
            for r in (b.get("runs") or [])
            if isinstance(r, dict)
        ),
    )

    summary_payload = {
        **base_summary,
        "headings_detected": headings_detected,
        "lists_detected": lists_detected,
        "tables_detected": tables_detected,
        "bold_emphasis_applied": bold_emphasis_applied,
        "revertible_blocks": revertible_blocks,
    }

    return {
        "document_id": document.id,
        "job_id": job.id,
        "status": job.status,
        "original": {
            "schema_version": raw_original.get("schema_version", "di.v1"),
            "doc_context": raw_original.get("doc_context") or {
                "document_type": doc_type,
                "body_font_size": body_font_size,
            },
            "blocks": original_blocks,
        },
        "proposed": {
            "schema_version": raw_proposed.get("schema_version", "di.v1"),
            "blocks": proposed_blocks,
        },
        "summary": summary_payload,
    }


@api_view(['GET'])
@permission_classes([AllowAny])
def document_structure_view(request, id):
    try:
        document = Document.objects.get(id=id)
    except Document.DoesNotExist:
        return Response({"error": "NOT_FOUND", "message": "El documento no existe."}, status=status.HTTP_404_NOT_FOUND)

    job = ProcessingJob.objects.filter(document=document).last()
    if not job:
        return Response({"error": "NOT_FOUND", "message": "Job de procesamiento no encontrado."}, status=status.HTTP_404_NOT_FOUND)

    if job.status != "review":
        return Response(
            {"error": "INVALID_STATE", "message": "El documento no se encuentra en estado de revisión."},
            status=status.HTTP_409_CONFLICT,
        )

    if (
        not isinstance(job.structure_original, dict)
        or "blocks" not in job.structure_original
        or not isinstance(job.structure_proposed, dict)
        or "blocks" not in job.structure_proposed
    ):
        return Response(
            {"error": "INVALID_STATE", "message": "El documento no cuenta con una propuesta de estructura válida."},
            status=status.HTTP_409_CONFLICT,
        )

    payload = _build_structure_response_payload(document, job)
    return Response(payload, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
def review_document_view(request, id):
    try:
        document = Document.objects.get(id=id)
    except Document.DoesNotExist:
        return Response({"error": "NOT_FOUND", "message": "El documento no existe."}, status=status.HTTP_404_NOT_FOUND)

    job = ProcessingJob.objects.filter(document=document).last()
    if not job:
        return Response({"error": "NOT_FOUND", "message": "Job de procesamiento no encontrado."}, status=status.HTTP_404_NOT_FOUND)

    if job.status != "review":
        return Response(
            {"error": "INVALID_STATE", "message": "El documento no se encuentra en estado de revisión."},
            status=status.HTTP_409_CONFLICT,
        )

    if not isinstance(request.data, Mapping):
        return Response(
            {"error": "INVALID_CONFIG", "message": "El cuerpo de la solicitud debe ser un objeto JSON válido."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    action = request.data.get("action")
    if action not in ("accept", "reject"):
        return Response(
            {"error": "INVALID_CONFIG", "message": "La acción debe ser 'accept' o 'reject'."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if action == "accept":
        revert_ids = request.data.get("revert", [])
        if revert_ids is None:
            revert_ids = []
        try:
            finalized = finalize_job(job, revert_ids)
        except ValueError as exc:
            return Response(
                {"error": "INVALID_CONFIG", "message": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except InvalidJobState as exc:
            return Response(
                {"error": "INVALID_STATE", "message": str(exc)},
                status=status.HTTP_409_CONFLICT,
            )

        if finalized.status == "error":
            return Response(
                {
                    "error": finalized.error_code or "PROCESSING_ERROR",
                    "message": finalized.error_message or "No se pudo procesar el documento.",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        ai_sum = finalized.ai_summary or {}
        return Response(
            {
                "document_id": document.id,
                "job_id": finalized.id,
                "status": finalized.status,
                "action": "accept",
                "summary": {
                    "headings_applied": ai_sum.get("headings_applied", ai_sum.get("headings_detected", 0)),
                    "lists_applied": ai_sum.get("lists_applied", ai_sum.get("lists_detected", 0)),
                    "tables_applied": ai_sum.get("tables_applied", ai_sum.get("tables_detected", 0)),
                    "reverted_blocks_count": ai_sum.get("reverted_blocks_count", 0),
                },
                "download_url": f"/api/documents/{document.id}/download/",
                "finished_at": finalized.finished_at,
            },
            status=status.HTTP_200_OK,
        )

    # action == "reject" -> Flujo de solo plantilla del Sprint 2 sobre el documento original
    claimed = ProcessingJob.objects.filter(pk=job.pk, status="review").update(
        status="processing",
        progress_stage="building",
        error_code=None,
        error_message=None,
    )
    if not claimed:
        return Response(
            {"error": "INVALID_STATE", "message": "El documento no se encuentra en estado de revisión."},
            status=status.HTTP_409_CONFLICT,
        )

    job.refresh_from_db()
    try:
        _run_template_only_formatting(document, job)

        rejected_summary = {
            **(job.ai_summary or {}),
            "headings_applied": 0,
            "lists_applied": 0,
            "tables_applied": 0,
            "reverted_blocks_count": 0,
            "restructured_blocks_count": 0,
        }
        job.ai_summary = rejected_summary
        job.status = "done"
        job.progress_stage = "building"
        job.progress_done = job.progress_total
        job.finished_at = timezone.now()
        job.save()

        return Response(
            {
                "document_id": document.id,
                "job_id": job.id,
                "status": job.status,
                "action": "reject",
                "summary": {
                    "headings_applied": 0,
                    "lists_applied": 0,
                    "tables_applied": 0,
                    "reverted_blocks_count": 0,
                },
                "download_url": f"/api/documents/{document.id}/download/",
                "finished_at": job.finished_at,
            },
            status=status.HTTP_200_OK,
        )
    except Exception as exc:
        mark_job_error(job.pk, exc)
        job.refresh_from_db()
        return Response(
            {
                "error": job.error_code or "PROCESSING_ERROR",
                "message": job.error_message or "No se pudo procesar el documento.",
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def download_document_view(request, id):
    try:
        document = Document.objects.get(id=id)
        job = ProcessingJob.objects.filter(document=document).last()
        
        if not job:
            return Response({"error": "JOB_NOT_FOUND"}, status=status.HTTP_404_NOT_FOUND)
            
        if job.status != 'done' or not job.result_file:
            return Response({"error": "NOT_READY", "message": "El documento aún no está listo."}, status=status.HTTP_409_CONFLICT)
            
        file_handle = job.result_file.open('rb')
        response = FileResponse(
            file_handle, 
            content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )
        
        name, ext = os.path.splitext(document.original_name)
        download_name = f"{name}_formateado{ext}"
        
        response['Content-Disposition'] = f'attachment; filename="{download_name}"'
        return response
        
    except Document.DoesNotExist:
        return Response({"error": "NOT_FOUND", "message": "El documento no existe."}, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
@permission_classes([AllowAny])
def list_templates_view(request):
    presets = list_presets()
    return Response({"presets": presets}, status=status.HTTP_200_OK)
