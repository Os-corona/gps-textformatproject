from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from .config import list_presets

@api_view(['GET'])
@permission_classes([AllowAny])
def list_templates_view(request):
    presets = list_presets()
    return Response({"presets": presets}, status=status.HTTP_200_OK)
