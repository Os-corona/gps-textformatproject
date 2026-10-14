from django.urls import path
from .views import extract_text_view, format_document_view
from .views import upload_document_view

urlpatterns = [
    path('extract/', extract_text_view, name='extract_text'),
    path('upload/', upload_document_view, name='upload_document'),
    path('<int:id>/format/', format_document_view, name='format_document'),
]