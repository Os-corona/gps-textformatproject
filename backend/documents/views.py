from django.db.migrations import serializer
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.models import User
from .docx_engine.extractor import extract_structure
from .serializers import DocumentUploadSerializer
from .models import Document, ProcessingJob
import io
from django.utils import timezone
from django.core.files.base import ContentFile
from docx import Document as DocxDocument
from pydantic import ValidationError
from .templates_engine.config import TemplateConfig, load_preset
from .pipeline import PIPELINE

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
        "original_name": document.original_name
    }, status=status.HTTP_201_CREATED)

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

    data = request.data.copy()
    preset_id = data.pop('preset_id', None)
    
    try:
        if preset_id:
            preset_config = load_preset(preset_id)
            config_dict = preset_config.model_dump()
            config_dict.update(data)
            config = TemplateConfig(**config_dict)
        else:
            config = TemplateConfig(**data)
    except ValidationError as e:
        return Response({"error": "INVALID_CONFIG", "message": e.errors()}, status=status.HTTP_400_BAD_REQUEST)
    except FileNotFoundError:
        return Response({"error": "INVALID_CONFIG", "message": f"El preset '{preset_id}' no existe."}, status=status.HTTP_400_BAD_REQUEST)

    job.config = config.model_dump()
    job.status = 'processing'
    job.started_at = timezone.now()
    job.save()

    try:
        doc_obj = DocxDocument(document.original_file)
        
        for step in PIPELINE:
            doc_obj = step(doc_obj, job)
            
        temp_io = io.BytesIO()
        doc_obj.save(temp_io)
        temp_io.seek(0)
        
        try:
            DocxDocument(temp_io)
            temp_io.seek(0)
        except Exception:
            raise Exception("El documento resultante quedó corrupto tras el formateo.")
            
        filename = f"result_{job.id}.docx"
        job.result_file.save(filename, ContentFile(temp_io.read()))
        
        job.status = 'done'
        job.finished_at = timezone.now()
        job.save()
        
        return Response({"status": job.status}, status=status.HTTP_200_OK)

    except Exception as e:
        # 8. Error general
        job.status = 'error'
        job.error_message = str(e)
        job.save()
        return Response({"error": "PROCESSING_ERROR", "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
