from django.test import TestCase
from django.contrib.auth.models import User
from .models import Document, ProcessingJob


class DocumentModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password123')

    def test_create_document(self):
        doc = Document.objects.create(
            user=self.user,
            original_file='uploads/tesis.docx',
            original_name='tesis.docx',
            size_bytes=248913,
        )
        self.assertEqual(doc.original_name, 'tesis.docx')
        self.assertEqual(doc.size_bytes, 248913)
        self.assertIn('tesis.docx', str(doc))

    def test_create_processing_job_defaults(self):
        doc = Document.objects.create(
            user=self.user,
            original_file='uploads/tesis.docx',
            original_name='tesis.docx',
            size_bytes=248913,
        )
        job = ProcessingJob.objects.create(document=doc)
        self.assertEqual(job.status, 'pending')
        self.assertEqual(job.config, {})
        self.assertFalse(job.use_ai)
        self.assertIsNone(job.ai_suggestions)
        self.assertIsNone(job.error_message)
        self.assertIsNone(job.started_at)
        self.assertIsNone(job.finished_at)
        self.assertIn('Job', str(job))

    def test_create_processing_job_with_fields(self):
        doc = Document.objects.create(
            user=self.user,
            original_file='uploads/tesis.docx',
            original_name='tesis.docx',
            size_bytes=248913,
        )
        sample_config = {
            'preset_id': 'apa7',
            'margins_cm': {'top': 2.54, 'bottom': 2.54, 'left': 2.54, 'right': 2.54},
            'font_family': 'Times New Roman',
            'font_size_pt': 12,
            'line_spacing': 2.0,
            'heading_sizes_pt': {'h1': 12, 'h2': 12, 'h3': 12},
            'use_ai': False,
        }
        job = ProcessingJob.objects.create(
            document=doc,
            status='done',
            config=sample_config,
            use_ai=False,
            ai_suggestions={'suggestions': []},
        )
        self.assertEqual(job.status, 'done')
        self.assertEqual(job.config['preset_id'], 'apa7')
        self.assertEqual(job.ai_suggestions, {'suggestions': []})
