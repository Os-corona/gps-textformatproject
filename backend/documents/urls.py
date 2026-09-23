from django.urls import path
from .views import extract_text_view

urlpatterns = [
    path('extract/', extract_text_view, name='extract_text'),
]