from django.urls import path
from .views import extract_text_view
from .views import upload_document_view

urlpatterns = [
    path('extract/', extract_text_view, name='extract_text'),
    path('upload/', upload_document_view, name='upload_document')
]