from pathlib import Path
import re

import pytest

from ai_engine.heuristic import structure
from ai_engine.providers import (FakeProvider, get_provider, ProviderAuthError,
    ProviderRateLimitError, ProviderUnavailableError, InvalidModelOutputError)
from common.document_schema import AIChunkInput, Hints, Run, SourceBlock
from common.integrity import validate_tokens
from docx_engine.extractor import extract_document

FIXTURES = Path(__file__).parent / 'fixtures'


def test_heading_fixture():
    di = extract_document(FIXTURES / '02_headings_mixto.docx')
    out = structure(AIChunkInput(chunk_id='headings', blocks=di.blocks))
    by_src = {b.src[0]: b for b in out.blocks}
    for text in ('1. RESUMEN', 'Observaciones importantes', 'Anexos'):
        source = next(b for b in di.blocks if b.text == text)
        assert by_src[source.id].type == 'heading'
        assert ''.join(r.text for r in by_src[source.id].runs) == text
    assert all(by_src[b.id].type == 'keep' for b in di.blocks if b.type == 'keep')
    for source in di.blocks:
        result = by_src[source.id]
        if result.type != 'keep':
            expected = source.text
            if result.type == 'list_item':
                expected = re.sub(r'^\s*[·◦▪•]\s*', '', expected)
            assert validate_tokens(expected, ''.join(r.text for r in result.runs)).is_valid


def test_list_fixture_and_integrity():
    di = extract_document(FIXTURES / '05_listas.docx')
    out = structure(AIChunkInput(chunk_id='lists', blocks=di.blocks))
    items = [b for b in out.blocks if b.type == 'list_item']
    assert len(items) == 18
    assert [b.level for b in items[:7]] == [1, 2, 3, 3, 2, 1, 2]
    assert sum(b.is_numbered for b in items) == 10
    for source, result in zip(di.blocks, out.blocks):
        if result.type == 'keep':
            assert result.src == [source.id]
            continue
        expected = source.text
        if result.type == 'list_item':
            expected = re.sub(r'^\s*(?:[·◦▪]\s*|\d+\.\s+)', '', expected)
        assert validate_tokens(expected, ''.join(r.text for r in result.runs)).is_valid


def test_consecutive_key_values_preserve_format_and_content():
    blocks = [SourceBlock(id='1', type='paragraph', runs=[Run(text='Nom'), Run(text='bre: Ana', italic=True)], hints=Hints()),
              SourceBlock(id='2', type='paragraph', runs=[Run(text='Edad: 20')], hints=Hints()),
              SourceBlock(id='3', type='paragraph', runs=[Run(text='Texto normal.')], hints=Hints())]
    out = structure(AIChunkInput(chunk_id='x', blocks=blocks))
    assert [(r.text, r.bold, r.italic) for r in out.blocks[0].runs] == [('Nom', True, None), ('bre:', True, True), (' Ana', None, True)]
    assert out.blocks[1].runs[0].bold is True
    assert blocks[0].runs[0].bold is None


def test_fake_provider_from_env(monkeypatch):
    monkeypatch.setenv('AI_PROVIDER', 'fake')
    monkeypatch.delenv('AI_API_KEY', raising=False)
    provider = get_provider()
    assert isinstance(provider, FakeProvider)
    assert provider.structure(AIChunkInput(chunk_id='id')).output.chunk_id == 'id'


@pytest.mark.parametrize(('error', 'exception'), [('auth', ProviderAuthError), ('rate_limit', ProviderRateLimitError), ('timeout', ProviderUnavailableError), ('invalid_output', InvalidModelOutputError)])
def test_fake_provider_errors(error, exception):
    with pytest.raises(exception):
        get_provider(provider_name='fake', error=error).structure(AIChunkInput(chunk_id='id'))
