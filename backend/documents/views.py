from django.shortcuts import render
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .services import extract_paragraphs

@api_view(['POST'])
def extract_text_view(request):
    if 'file' not in request.FILES:
        return Response({"error": "No se proporcionó ningún archivo."}, status=status.HTTP_400_BAD_REQUEST)

    uploaded_file = request.FILES['file']

    if not uploaded_file.name.endswith('.docx'):
        return Response({"error": "El archivo debe ser un documento .docx."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        extracted_paragraphs = extract_paragraphs(uploaded_file)
        return Response({
            'filename': uploaded_file.name,
            'total_paragraphs': len(extracted_paragraphs),
            'paragraphs': extracted_paragraphs
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({"error": f'Error al procesar el documento: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)