from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.models import User
from .docx_engine.extractor import extract_structure
from .serializers import DocumentUploadSerializer
from .models import Document, ProcessingJob

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

# --- AQUI VAN LOS DECORADORES PARA TU NUEVO ENDPOINT ---
@api_view(['POST'])
@permission_classes([AllowAny])
def upload_document_view(request):
    serializer = DocumentUploadSerializer(data=request.data)
    
    if not serializer.is_valid():
        error_dict = serializer.errors.get('file', [{}])[0]
        code = error_dict.get('code', 'INVALID_FILE')
        message = error_dict.get('message', 'Error de validación desconocido.')
        return Response({"error": code, "message": message}, status=status.HTTP_400_BAD_REQUEST)
        
    uploaded_file = serializer.validated_data['file']
    
    dev_user, created = User.objects.get_or_create(username="dev_user", defaults={"email": "dev@test.com"})
    
    document = Document.objects.create(
        user=dev_user,
        file=uploaded_file,
        original_name=uploaded_file.name,
        file_size=uploaded_file.size
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