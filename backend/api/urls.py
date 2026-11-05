from django.urls import path
from .views import (
    extract_text_view,
    upload_document_view,
    format_document_view,
    document_status_view,
    download_document_view,
    list_templates_view,
)

urlpatterns = [
    path('documents/', upload_document_view, name='upload_document_root'),
    path('documents/upload/', upload_document_view, name='upload_document'),
    path('documents/extract/', extract_text_view, name='extract_text'),
    path('documents/<int:id>/', document_status_view, name='document_status'),
    path('documents/<int:id>/format/', format_document_view, name='format_document'),
    path('documents/<int:id>/download/', download_document_view, name='download_document'),
    path('documents/templates/', list_templates_view, name='list_templates_documents'),
    path('templates/', list_templates_view, name='list_templates'),
]

