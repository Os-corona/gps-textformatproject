from django.urls import path
from .views import (
    extract_text_view,
    upload_document_view,
    format_document_view,
    document_detail_view,
    download_document_view,
)

urlpatterns = [
    path('', upload_document_view, name='upload_document_root'),
    path('upload/', upload_document_view, name='upload_document'),
    path('extract/', extract_text_view, name='extract_text'),
    path('<int:id>/', document_detail_view, name='document_detail'),
    path('<int:id>/format/', format_document_view, name='format_document'),
    path('<int:id>/download/', download_document_view, name='download_document'),
]