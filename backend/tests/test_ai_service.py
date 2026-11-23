"""Provider calls, feedback, fallback and document-level summaries without network."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from django.test import override_settings

from ai_engine.chunker import DocumentTooLargeForAI
from ai_engine.providers.base import (
    AINotConfiguredError,
    InvalidModelOutputError,
    ProviderAuthError,
    ProviderResult,
    ProviderUnavailableError,
    TokenUsage,
)
from ai_engine.providers.fake import FakeProvider
from ai_engine.service import structure_document
from common.document_schema import DocumentIntermediate, SourceBlock
from docx_engine.extractor import extract_document


def document(text="Total $10."):
    return DocumentIntermediate(blocks=[SourceBlock(id="b1", type="paragraph", text=text)])


def response(text="Total $10.", *, chunk_id="chunk-001", generated=False):
    blocks = [{"type": "paragraph", "src": ["b1"], "runs": [{"text": text}]}]
    if generated:
        blocks.insert(0, {"type": "heading", "level": 2, "generated": True,
                          "src": ["b1"], "runs": [{"text": "Resumen"}]})
    return SimpleNamespace(output={"chunk_id": chunk_id, "blocks": blocks})


def test_success_without_retry_and_generated_summary():
    provider = Mock()
    provider.structure.return_value = response(generated=True)
    result = structure_document(document(), {"emphasis": "none"}, provider)
    provider.structure.assert_called_once()
    chunk = provider.structure.call_args.args[0]
    assert chunk.metadata["ai_options"] == {"emphasis": "none"}
    assert result.summary == {
        "chunks_total": 1, "chunks_ai": 1, "chunks_retried": 0,
        "chunks_heuristic": 0, "blocks_by_type": {"heading": 1, "paragraph": 1},
        "generated_elements": 1,
    }
    assert result.reports[0].ok


def test_retry_includes_integrity_violations_then_accepts():
    provider = Mock()
    provider.structure.side_effect = [response("Total $11."), response()]
    result = structure_document(document(), {}, provider)
    assert provider.structure.call_count == 2
    assert provider.structure.call_args_list[0].kwargs["feedback"] is None
    feedback = provider.structure.call_args_list[1].kwargs["feedback"]
    assert '"type": "CRITICAL_DATA"' in feedback
    assert '"src": ["b1"]' in feedback
    assert result.summary["chunks_retried"] == 1
    assert result.summary["chunks_ai"] == 1
    assert result.summary["chunks_heuristic"] == 0
    assert [r.ok for r in result.reports] == [False, True]


@pytest.mark.parametrize("bad", [
    response("Total $99."),
    response(chunk_id="wrong"),
    SimpleNamespace(output={"chunk_id": "chunk-001", "blocks": [{"type": "unknown"}]}),
    InvalidModelOutputError("JSON inválido"),
    ProviderUnavailableError("Proveedor no disponible"),
])
def test_two_failures_use_heuristic_without_interrupting(bad):
    provider = Mock()
    provider.structure.side_effect = [bad, bad]
    result = structure_document(document(), {}, provider)
    assert provider.structure.call_count == 2
    assert result.summary["chunks_heuristic"] == 1
    assert result.summary["chunks_retried"] == 1
    assert result.summary["chunks_ai"] == 0
    assert "".join(r.text for r in result.blocks[0].runs) == "Total $10."


def test_fallback_does_not_interrupt_later_chunks():
    di = DocumentIntermediate(blocks=[
        SourceBlock(id="b1", type="paragraph", text="Primero."),
        SourceBlock(id="k", type="keep", xml="<original/>"),
        SourceBlock(id="b2", type="paragraph", text="Segundo."),
    ])
    provider = Mock()

    def structure(chunk, feedback=None):
        if chunk.chunk_id == "chunk-001":
            return SimpleNamespace(output={"chunk_id": chunk.chunk_id, "blocks": []})
        return SimpleNamespace(output={"chunk_id": chunk.chunk_id, "blocks": [
            {"type": "paragraph", "src": ["b2"], "runs": [{"text": "Segundo."}]},
        ]})

    provider.structure.side_effect = structure
    with override_settings(AI_MAX_CHUNK_CHARS=8):
        result = structure_document(di, {}, provider)
    assert result.summary["chunks_total"] == 2
    assert result.summary["chunks_ai"] == 1
    assert result.summary["chunks_heuristic"] == 1
    assert result.summary["chunks_retried"] == 1
    assert [b.src for b in result.blocks] == [["b1"], ["k"], ["b2"]]
    assert result.summary["blocks_by_type"] == {"paragraph": 2, "keep": 1}


def test_empty_document_never_calls_provider():
    provider = Mock()
    result = structure_document(DocumentIntermediate(), {}, provider)
    provider.structure.assert_not_called()
    assert result.blocks == []
    assert result.summary["chunks_total"] == 0


def test_size_limit_checked_before_provider_call():
    provider = Mock()
    with pytest.raises(DocumentTooLargeForAI):
        structure_document(document("x" * 60001), {}, provider)
    provider.structure.assert_not_called()


def test_provider_initialization_failure_uses_fallback(monkeypatch):
    monkeypatch.setattr("ai_engine.service.get_provider", Mock(side_effect=ProviderUnavailableError("Unavailable")))
    result = structure_document(document())
    assert result.summary["chunks_heuristic"] == 1
    assert result.summary["chunks_retried"] == 0


@pytest.mark.parametrize("exc_cls", [AINotConfiguredError, ProviderAuthError])
def test_auth_and_configuration_errors_propagate_immediately(monkeypatch, exc_cls):
    monkeypatch.setattr("ai_engine.service.get_provider", Mock(side_effect=exc_cls("Auth/Config error")))
    with pytest.raises(exc_cls):
        structure_document(document())


def test_provider_auth_error_during_call_propagates_without_retry():
    provider = Mock()
    provider.structure.side_effect = ProviderAuthError("401 Unauthorized")
    with pytest.raises(ProviderAuthError):
        structure_document(document(), {}, provider)
    provider.structure.assert_called_once()


def test_fake_provider_passes_all_real_docx_fixtures():
    fixtures_dir = Path(__file__).resolve().parent / "fixtures"
    for docx_path in sorted(fixtures_dir.glob("*.docx")):
        di = extract_document(docx_path)
        result = structure_document(di, {}, FakeProvider())
        assert result.summary["chunks_heuristic"] == 0, f"{docx_path.name} fell back to heuristic"
        assert result.summary["chunks_ai"] == result.summary["chunks_total"]


def test_generated_header_cells_counted_individually():
    provider = Mock()
    provider.structure.return_value = SimpleNamespace(output={"chunk_id": "chunk-001", "blocks": [{
        "type": "table", "src": ["b1", "b2"], "header_row": True,
        "rows": [[{"text": "Campo", "generated": True}, {"text": "Valor", "generated": True}],
                 [{"text": "Nombre"}, {"text": "Ana"}],
                 [{"text": "Nombre"}, {"text": "Luis"}]],
    }]})
    di = DocumentIntermediate(blocks=[
        SourceBlock(id="b1", type="paragraph", text="Nombre: Ana"),
        SourceBlock(id="b2", type="paragraph", text="Nombre: Luis"),
    ])
    result = structure_document(di, {}, provider)
    assert result.summary["chunks_ai"] == 1
    assert result.summary["generated_elements"] == 2
    assert result.summary["blocks_by_type"] == {"table": 1}


def test_provider_cannot_mutate_the_validation_reference():
    di = document()
    provider = Mock()

    def mutate(chunk, feedback=None):
        chunk.blocks[0].text = "Total $99."
        return response("Total $99.")

    provider.structure.side_effect = mutate
    result = structure_document(di, {}, provider)
    assert di.blocks[0].text == "Total $10."
    assert result.summary["chunks_heuristic"] == 1
    assert "".join(r.text for r in result.blocks[0].runs) == "Total $10."


def test_progress_callback_and_usage_include_both_integrity_attempts():
    from common.document_schema import AIChunkOutput

    usage = TokenUsage(input_tokens=10, output_tokens=5, model="offline", provider="fake", attempts=2)
    provider = Mock()
    provider.structure.side_effect = [
        ProviderResult(output=AIChunkOutput.model_validate(response("Total $99.").output), usage=usage),
        ProviderResult(output=AIChunkOutput.model_validate(response().output), usage=usage),
    ]
    progress = Mock()
    result = structure_document(document(), {}, provider, on_progress=progress)
    assert result.usage == {
        "input_tokens": 20, "output_tokens": 10, "total_tokens": 30,
        "calls": 2, "attempts": 4, "models": ["offline"], "providers": ["fake"],
    }
    assert progress.call_args_list[0].args == ("structuring", 0, 1)
    assert progress.call_args_list[-1].args == ("validating", 1, 1)
    assert all(call.args[1] == 0 for call in progress.call_args_list[:-1])


def test_bold_ratio_only_violation_is_sanitized_without_discarding_ai_structure():
    provider = Mock()
    provider.structure.return_value = SimpleNamespace(output={
        "chunk_id": "chunk-001",
        "blocks": [
            {"type": "heading", "level": 2, "generated": True, "src": ["b1"], "runs": [{"text": "Resumen", "bold": True}]},
            {"type": "paragraph", "src": ["b1"], "runs": [{"text": "Total $10.", "bold": True}]},
        ],
    })
    result = structure_document(document(), {"creative_structure": True}, provider)
    provider.structure.assert_called_once()
    assert result.summary["chunks_ai"] == 1
    assert result.summary["chunks_heuristic"] == 0
    assert result.summary["blocks_by_type"] == {"heading": 1, "paragraph": 1}
    assert all(not r.bold for b in result.blocks for r in b.runs)
