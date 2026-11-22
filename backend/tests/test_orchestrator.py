"""S3T19: persistent sync/thread orchestration and exact XML reversions, offline."""
from copy import deepcopy
from io import BytesIO
from threading import Event
from unittest.mock import Mock

import pytest
from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.db import transaction
from docx import Document as DocxDocument
from lxml import etree
from rest_framework.test import APIClient

from ai_engine.providers.fake import FakeProvider
from ai_engine.service import structure_document
from documents.models import Document, ProcessingJob
from orchestrator import ai_pipeline, runner

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture(autouse=True)
def offline_settings(settings, monkeypatch, tmp_path):
    settings.JOB_RUNNER = "sync"
    settings.MEDIA_ROOT = str(tmp_path / "media")
    monkeypatch.setenv("AI_PROVIDER", "fake")
    yield
    runner.shutdown_runner()


@pytest.fixture
def make_job():
    user = User.objects.create_user(username="job-test")

    def create(texts=("Un documento con contenido original.",), *, doc=None):
        if doc is None:
            doc = DocxDocument()
            for text in texts:
                doc.add_paragraph(text)
        content = BytesIO()
        doc.save(content)
        raw = content.getvalue()
        document = Document.objects.create(
            user=user, original_file=ContentFile(raw, name="original.docx"),
            original_name="original.docx", size_bytes=len(raw),
        )
        return ProcessingJob.objects.create(document=document, use_ai=True, config={"font_family": "Arial", "font_size_pt": 12})

    return create


def test_sync_flow_processing_review_done_with_progress(make_job, monkeypatch, settings):
    settings.AI_MAX_CHUNK_CHARS = 100
    job = make_job(["Párrafo con texto original. " * 3 for _ in range(4)])
    events = []

    def track(di, options, *, on_progress):
        def progress(stage, done, total):
            on_progress(stage, done, total)
            snapshot = ProcessingJob.objects.get(pk=job.pk)
            events.append((snapshot.status, snapshot.progress_stage, snapshot.progress_done, snapshot.progress_total))
        return structure_document(di, options, on_progress=progress)

    monkeypatch.setattr(ai_pipeline, "structure_document", track)
    future = runner.enqueue(job.pk)
    assert future.done()
    job.refresh_from_db()
    assert job.status == "review"
    assert job.started_at and not job.finished_at
    assert not job.result_file
    assert job.structure_original["blocks"]
    assert job.structure_proposed == job.ai_suggestions
    assert job.progress_done == job.progress_total == 4
    assert {s for _, s, _, _ in events} == {"structuring", "validating"}
    assert all(status == "processing" for status, _, _, _ in events)
    assert [done for _, _, done, _ in events] == sorted(done for _, _, done, _ in events)
    assert {done for _, stage, done, _ in events if stage == "validating"} >= {1, 2, 3, 4}
    assert job.ai_usage["calls"] == 4
    assert job.ai_usage["providers"] == ["fake"]
    assert not job.ai_summary["fallback_only"]
    assert job.ai_summary["chunks_total"] == 4

    original_bytes = job.document.original_file.read()
    finalized = ai_pipeline.finalize_job(job, [])
    assert finalized.status == "done"
    assert finalized.progress_stage == "building"
    assert finalized.progress_done == finalized.progress_total
    assert finalized.finished_at >= finalized.started_at
    assert finalized.ai_summary["reverted_blocks_count"] == 0
    with finalized.result_file.open("rb") as result:
        doc = DocxDocument(result)
    assert [p.text for p in doc.paragraphs] == ["Párrafo con texto original. " * 3] * 4
    assert doc.styles["Normal"].font.name == "Arial"
    with job.document.original_file.open("rb") as original:
        assert original.read() == original_bytes


def test_exact_original_xml_is_restored_before_template(make_job, monkeypatch):
    doc = DocxDocument()
    p = doc.add_paragraph()
    run = p.add_run("• Elemento original")
    run.italic = True
    p.paragraph_format.keep_with_next = True
    original_xml = etree.tostring(p._p)
    job = make_job(doc=doc)
    runner.enqueue(job.pk).result()
    job.refresh_from_db()
    assert job.structure_proposed["blocks"][0]["type"] == "list_item"
    original_template = ai_pipeline.apply_template
    observed = []

    def check_xml(rebuilt, config):
        observed.append(etree.tostring(rebuilt.paragraphs[0]._p))
        original_template(rebuilt, config)

    monkeypatch.setattr(ai_pipeline, "apply_template", check_xml)
    ai_pipeline.finalize_job(job, ["b0"])
    assert observed == [original_xml]
    assert job.status == "done"
    assert job.ai_summary["reverted_source_ids"] == ["b0"]
    with job.result_file.open("rb") as result:
        assert DocxDocument(result).paragraphs[0].text == "• Elemento original"


def test_merged_table_reversion_restores_all_originals(make_job):
    job = make_job(["Nombre: Ana", "Nombre: Luis"])
    runner.enqueue(job.pk).result()
    job.refresh_from_db()
    trailing = deepcopy(job.structure_proposed["blocks"][2:])
    job.structure_proposed["blocks"] = [{
        "type": "table", "src": ["b0", "b1"], "header_row": True,
        "rows": [[{"text": "Campo", "generated": True}, {"text": "Valor", "generated": True}],
                 [{"text": "Nombre"}, {"text": "Ana"}],
                 [{"text": "Nombre"}, {"text": "Luis"}]],
    }] + trailing
    job.save(update_fields=["structure_proposed"])
    ai_pipeline.finalize_job(job, ["b0"])
    assert job.status == "done"
    assert job.ai_summary["reverted_blocks_count"] == 2
    with job.result_file.open("rb") as result:
        doc = DocxDocument(result)
    assert not doc.tables
    assert [p.text for p in doc.paragraphs] == ["Nombre: Ana", "Nombre: Luis"]


def test_split_block_is_restored_once_and_anchored_generated_heading_removed():
    original = {"blocks": [{"id": "b0"}, {"id": "b1"}]}
    proposed = {"blocks": [
        {"type": "heading", "src": ["b0"], "generated": True},
        {"type": "list_item", "src": ["b0"]},
        {"type": "list_item", "src": ["b0"]},
        {"type": "paragraph", "src": ["b1"]},
    ]}
    snapshot = deepcopy(proposed)
    result, ids = ai_pipeline.restore_original_blocks(original, proposed, ["b0", "b0"])
    assert result["blocks"] == [{"type": "keep", "id": "b0", "src": ["b0"]}, proposed["blocks"][-1]]
    assert ids == ["b0"]
    assert proposed == snapshot


@pytest.mark.parametrize("ids", [["unknown"], "b0", [1]])
def test_invalid_reversions_leave_job_in_review(make_job, ids):
    job = make_job()
    runner.enqueue(job.pk).result()
    with pytest.raises(ValueError):
        ai_pipeline.finalize_job(job, ids)
    job.refresh_from_db()
    assert job.status == "review"
    assert not job.result_file


def test_finalize_requires_review_and_cannot_run_twice(make_job):
    job = make_job()
    with pytest.raises(ai_pipeline.InvalidJobState):
        ai_pipeline.finalize_job(job, [])
    runner.enqueue(job.pk).result()
    ai_pipeline.finalize_job(job, [])
    with pytest.raises(ai_pipeline.InvalidJobState):
        ai_pipeline.finalize_job(job, [])


@pytest.mark.parametrize("failure", ["timeout", "invalid_output", "rate_limit"])
def test_all_fallback_chunks_continue_to_review_and_done(make_job, monkeypatch, failure):
    monkeypatch.setattr("ai_engine.service.get_provider", lambda: FakeProvider(error=failure))
    job = make_job()
    runner.enqueue(job.pk).result()
    job.refresh_from_db()
    assert job.status == "review"
    assert job.ai_summary["fallback_only"] is True
    assert job.ai_summary["chunks_fallback"] == job.ai_summary["chunks_total"]
    assert job.error_code is None
    ai_pipeline.finalize_job(job, [])
    assert job.status == "done"


def test_auth_failure_maps_to_configuration_error_without_details(make_job, monkeypatch):
    monkeypatch.setattr("ai_engine.service.get_provider", lambda: FakeProvider(error="auth"))
    job = make_job()
    runner.enqueue(job.pk).result()
    job.refresh_from_db()
    assert job.status == "error"
    assert job.error_code == "AI_NOT_CONFIGURED"
    assert "Simulated" not in job.error_message
    assert not job.result_file


def test_missing_provider_key_maps_to_configuration_error(make_job, monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "openrouter")
    monkeypatch.setenv("AI_API_KEY", "")
    job = make_job()
    runner.enqueue(job.pk).result()
    job.refresh_from_db()
    assert job.status == "error"
    assert job.error_code == "AI_NOT_CONFIGURED"


def test_document_limit_is_checked_before_provider(make_job, monkeypatch, settings):
    settings.AI_MAX_DOC_CHARS = 5
    provider_factory = Mock()
    monkeypatch.setattr("ai_engine.service.get_provider", provider_factory)
    job = make_job()
    runner.enqueue(job.pk).result()
    job.refresh_from_db()
    assert job.status == "error"
    assert job.error_code == "DOCUMENT_TOO_LARGE_FOR_AI"
    provider_factory.assert_not_called()


def test_unexpected_error_is_safe_in_database_and_status_api(make_job, monkeypatch):
    monkeypatch.setattr(ai_pipeline, "extract_document", Mock(side_effect=RuntimeError("Traceback: secret internal path")))
    job = make_job()
    runner.enqueue(job.pk).result()
    job.refresh_from_db()
    assert job.status == "error"
    assert job.error_code == "PROCESSING_ERROR"
    response = APIClient().get(f"/api/documents/{job.document_id}/")
    assert response.status_code == 200
    assert response.data["error_code"] == "PROCESSING_ERROR"
    assert "secret" not in str(response.data)
    assert "Traceback" not in str(response.data)


@pytest.mark.parametrize("failure", ["template", "integrity", "storage"])
def test_finalization_errors_never_publish_a_result(make_job, monkeypatch, failure):
    job = make_job()
    runner.enqueue(job.pk).result()
    if failure == "template":
        monkeypatch.setattr(ai_pipeline, "apply_template", Mock(side_effect=RuntimeError("secret")))
    elif failure == "integrity":
        def corrupt(doc, config):
            doc.paragraphs[0].text = "Contenido alterado 999"
        monkeypatch.setattr(ai_pipeline, "apply_template", corrupt)
    else:
        monkeypatch.setattr(job.result_file.storage, "save", Mock(side_effect=OSError("secret storage path")))
    ai_pipeline.finalize_job(job, [])
    assert job.status == "error"
    assert job.error_code == "PROCESSING_ERROR"
    assert "secret" not in job.error_message
    assert not job.result_file


def test_enqueue_waits_for_commit(make_job):
    job = make_job()
    with transaction.atomic():
        future = runner.enqueue(job.pk)
        assert not future.done()
        job.refresh_from_db()
        assert job.status == "pending"
    assert future.done()
    job.refresh_from_db()
    assert job.status == "review"


def test_rollback_never_launches_worker(make_job, monkeypatch):
    job = make_job()
    work = Mock()
    monkeypatch.setattr(runner, "run_ai_structuring", work)
    with pytest.raises(RuntimeError):
        with transaction.atomic():
            runner.enqueue(job.pk)
            raise RuntimeError("rollback")
    work.assert_not_called()
    job.refresh_from_db()
    assert job.status == "pending"


def test_duplicate_enqueue_does_not_process_review_again(make_job, monkeypatch):
    job = make_job()
    extract = Mock(wraps=ai_pipeline.extract_document)
    monkeypatch.setattr(ai_pipeline, "extract_document", extract)
    runner.enqueue(job.pk).result()
    assert runner.enqueue(job.pk).result() is None
    assert extract.call_count == 1


def test_thread_runner_is_nonblocking_and_claims_once(make_job, monkeypatch, settings):
    settings.JOB_RUNNER = "thread"
    started, release = Event(), Event()

    class SlowFake(FakeProvider):
        def structure(self, chunk_input, *, feedback=None):
            started.set()
            assert release.wait(10)
            return super().structure(chunk_input, feedback=feedback)

    monkeypatch.setattr("ai_engine.service.get_provider", SlowFake)
    job = make_job()
    future = runner.enqueue(job.pk)
    try:
        assert started.wait(5)
        assert not future.done()
        job.refresh_from_db()
        assert job.status == "processing"
        assert job.progress_stage == "structuring"
        duplicate = runner.enqueue(job.pk)
        assert duplicate.result(timeout=5) is None
    finally:
        release.set()
    assert future.result(timeout=10).status == "review"


def test_invalid_runner_backend_is_rejected(make_job, settings):
    settings.JOB_RUNNER = "unknown"
    job = make_job()
    with pytest.raises(ValueError):
        runner.enqueue(job.pk)
    job.refresh_from_db()
    assert job.status == "pending"


def test_ai_format_returns_202_and_exposes_persisted_progress(make_job):
    job = make_job()
    client = APIClient()
    response = client.post(f"/api/documents/{job.document_id}/format/", {"preset_id": "reporte", "use_ai": True}, format="json")
    assert response.status_code == 202
    response = client.get(f"/api/documents/{job.document_id}/")
    assert response.data["status"] == "review"
    assert response.data["progress"]["done"] == response.data["progress"]["total"]
    assert response.data["ai_summary"]["chunks_total"] > 0
    assert response.data["ai_usage"]["calls"] > 0
    assert response.data["download_url"] is None


def test_processing_job_cannot_be_started_again(make_job):
    job = make_job()
    job.status = "processing"
    job.progress_stage = "structuring"
    job.save()
    response = APIClient().post(f"/api/documents/{job.document_id}/format/", {"preset_id": "reporte", "use_ai": True}, format="json")
    assert response.status_code == 409
    assert response.data["error"] == "INVALID_STATE"


def test_api_thread_mode_returns_without_executing_inline(make_job, monkeypatch, settings):
    settings.JOB_RUNNER = "thread"
    executor = Mock()
    monkeypatch.setattr(runner, "_get_executor", lambda: executor)
    job = make_job()
    response = APIClient().post(f"/api/documents/{job.document_id}/format/", {"preset_id": "reporte", "use_ai": True}, format="json")
    assert response.status_code == 202
    executor.submit.assert_called_once_with(runner._thread_run, job.pk)
    job.refresh_from_db()
    assert job.status == "processing"
    assert job.progress_stage == "queued"


def test_thread_submission_failure_sets_safe_job_error(make_job, monkeypatch, settings):
    settings.JOB_RUNNER = "thread"
    executor = Mock()
    executor.submit.side_effect = RuntimeError("secret internal pool failure")
    monkeypatch.setattr(runner, "_get_executor", lambda: executor)
    job = make_job()
    future = runner.enqueue(job.pk)
    with pytest.raises(RuntimeError):
        future.result()
    job.refresh_from_db()
    assert job.status == "error"
    assert job.error_code == "PROCESSING_ERROR"
    assert "secret" not in job.error_message


def test_reverting_all_also_removes_unanchored_generated_headings():
    original = {"blocks": [{"id": "b0"}]}
    proposed = {"blocks": [
        {"type": "heading", "generated": True, "src": []},
        {"type": "paragraph", "src": ["b0"]},
    ]}
    restored, ids = ai_pipeline.restore_original_blocks(original, proposed, ["b0"])
    assert ids == ["b0"]
    assert restored["blocks"] == [{"type": "keep", "id": "b0", "src": ["b0"]}]
