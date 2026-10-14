from django.contrib import admin
from .models import Document, ProcessingJob


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('id', 'original_name', 'size_bytes', 'user', 'uploaded_at')
    search_fields = ('original_name', 'user__username')
    list_filter = ('uploaded_at',)


@admin.register(ProcessingJob)
class ProcessingJobAdmin(admin.ModelAdmin):
    list_display = ('id', 'document', 'status', 'use_ai', 'started_at', 'finished_at', 'created_at')
    list_filter = ('status', 'use_ai', 'created_at')
    search_fields = ('document__original_name', 'error_message')
    readonly_fields = ('created_at',)
