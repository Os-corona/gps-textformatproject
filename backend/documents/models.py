from django.db import models
from django.contrib.auth.models import User


class Document(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    original_file = models.FileField(upload_to='uploads/')
    original_name = models.CharField(max_length=255)
    size_bytes = models.PositiveIntegerField()
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.original_name} (ID: {self.id})"


class ProcessingJob(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pendiente"),
        ("processing", "Procesando"),
        ("review", "En revisión"),
        ("done", "Completado"),
        ("error", "Error"),
    ]

    document = models.ForeignKey(Document, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    config = models.JSONField(default=dict, blank=True)
    result_file = models.FileField(upload_to='results/', null=True, blank=True)
    error_message = models.TextField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    use_ai = models.BooleanField(default=False)
    ai_suggestions = models.JSONField(null=True, blank=True)
    progress_stage = models.CharField(max_length=30, blank=True, default="")
    progress_done = models.PositiveIntegerField(default=0)
    progress_total = models.PositiveIntegerField(default=0)
    ai_summary = models.JSONField(null=True, blank=True)
    ai_usage = models.JSONField(null=True, blank=True)
    error_code = models.CharField(max_length=64, null=True, blank=True)
    structure_original = models.JSONField(null=True, blank=True)
    structure_proposed = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Job {self.id} - Doc {self.document_id} ({self.status})"
