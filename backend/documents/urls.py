from django.urls import path
from .views import extract_text_view, format_document_view
from .views import extract_text_view
from .views import upload_document_view
from .views import document_status_view
from .views import download_document_view
from .views import list_templates_view

urlpatterns = [
    path('extract/', extract_text_view, name='extract_text'),
    path('upload/', upload_document_view, name='upload_document'),
    path('<int:id>/format/', format_document_view, name='format_document'),
    path('<int:id>/', document_status_view, name='document_status'),
    path('<int:id>/download/', download_document_view, name='download_document'),
    path('templates/', list_templates_view, name='list_templates'),
]