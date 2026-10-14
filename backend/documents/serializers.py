import os
from rest_framework import serializers
from docx import Document as DocxDocument

class DocumentUploadSerializer(serializers.Serializer):
    file = serializers.FileField()

    def validate_file(self, value):
        ext = os.path.splitext(value.name)[1].lower()
        if ext != '.docx':
            raise serializers.ValidationError("El archivo debe tener extensión .docx.", code="INVALID_FILE")
        
        if value.size > 10 * 1024 * 1024:
            raise serializers.ValidationError("El archivo excede el límite de 10 MB.", code="FILE_TOO_LARGE")
        
        header = value.read(4)
        value.seek(0)
        if header != b'PK\x03\x04':
            raise serializers.ValidationError("El archivo no es un documento válido, es antiguo o está protegido.", code="INVALID_FILE")

        try:
            DocxDocument(value)
            value.seek(0)
        except Exception:
            raise serializers.ValidationError("El documento está corrupto o no se pudo analizar.", code="INVALID_FILE")
        
        return value