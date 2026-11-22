"""S3T18: table-driven integrity acceptance and rejection cases."""
import pytest
from django.test import override_settings
from pydantic import ValidationError

from ai_engine.validator import validate_chunk
from common.document_schema import AIChunkOutput, HeadingOutBlock, IntegrityReport, TableCell


def source(text, id="b1", **extra):
    return {"id": id, "type": "paragraph", "text": text, **extra}


def out(text, src="b1", kind="paragraph", **extra):
    return {"type": kind, "src": [src], "runs": [{"text": text}], **extra}


def table(rows, refs=("b1", "b2"), header=True):
    return {"type": "table", "src": list(refs), "header_row": header,
            "rows": [[c if isinstance(c, dict) else {"text": c} for c in row] for row in rows]}


@pytest.mark.parametrize("inputs,outputs,code", [
    ([source("Total $125.50 y 15%.")], [out("Total $125.60 y 15%.")], "CRITICAL_DATA"),
    ([source("Total €20.")], [out("Total $20.")], "CRITICAL_DATA"),
    ([source("Porcentaje 15%.")], [out("Porcentaje 15.")], "CRITICAL_DATA"),
    ([source("Saldo -50")], [out("Saldo 50")], "CRITICAL_DATA"),
    ([source("-50")], [out("50", kind="list_item")], "CRITICAL_DATA"),
    ([source("Valores 10 y 20")], [out("Valores 20 y 10")], "CRITICAL_DATA"),
    ([source("primero"), source("segundo", "b2")], [out("primero")], "SOURCE_OMITTED"),
    ([source("primero"), source("segundo", "b2")], [out("segundo", "b2"), out("primero")], "SOURCE_ORDER"),
    ([source("Texto"), {"id": "k", "type": "keep"}], [out("Texto")], "KEEP_COUNT"),
    ([{"id": "k", "type": "keep"}], [{"type": "keep", "src": ["k"]}] * 2, "KEEP_COUNT"),
    ([source("Texto"), {"id": "k", "type": "keep"}], [{"type": "keep", "src": ["k"]}, out("Texto")], "SOURCE_ORDER"),
    ([{"id": "k", "type": "keep"}], [out("inventado", "k")], "KEEP_CHANGED"),
    ([source("Texto real")], [out("Texto inventado")], "TOKEN_RETENTION"),
    ([source("Texto real")], [out("Texto real inventado")], "ADDED_TOKENS"),
    ([source("Texto real")], [out("Texto real", generated=True)], "INVALID_SCHEMA"),
    ([source("Texto real")], [out("Texto real", src="desconocido")], "INVALID_SRC"),
    ([source("Texto real")], [out("Texto real", runs=[{"text": "Texto real", "bold": True}])], "BOLD_RATIO"),
    ([source("Título.")], [out("Título.", kind="heading", level=1)], "HEADING_SHAPE"),
    ([source("Título")], [out("Título", kind="heading", level=4)], "HEADING_LEVEL"),
    ([source("Texto")], [out("Texto"), out("Uno dos tres cuatro cinco seis siete", kind="heading", level=2, generated=True)], "GENERATED_LENGTH"),
    ([source("Texto")], [out("Texto"), out("Título", kind="heading", level=0, generated=True)], "GENERATED_LOCATION"),
    ([source("Texto")], [out("Texto"), out("Resumen 99", kind="heading", level=2, generated=True)], "CRITICAL_DATA"),
    ([source("Nombre: Ana")], [table([["Nombre", "Ana"]], refs=("b1",), header=False)], "TABLE_SHAPE"),
    ([source("Nombre: Ana")], [table([["Nombre", "Ana"], ["extra"]], refs=("b1",))], "INVALID_SCHEMA"),
    ([source("Nombre: Ana")], [table([["Nombre", "Valor"], [{"text": "Ana", "generated": True}, "extra"]], refs=("b1",))], "INVALID_SCHEMA"),
    ([source("Texto real")], [out("Texto real"), out("Texto real")], "SOURCE_DUPLICATED"),
    ([source("Alfa beta gamma")], [out("Alfa gamma beta")], "TOKEN_ORDER"),
    ([source("Nombre: Ana"), source("Nombre: Luis", "b2")], [table([["Nombre", "Valor"], ["Nombre", "Ana"], ["Nombre", "Luis"]])], "ADDED_TOKENS"),
])
def test_invalid_cases(inputs, outputs, code):
    report = validate_chunk(inputs, outputs)
    assert not report.ok
    assert code in {v.type for v in report.violations}
    assert report.errors
    assert all(v.src for v in report.violations)


@pytest.mark.parametrize("inputs,outputs", [
    ([source("Texto íntegro.")], [out("Texto íntegro.")]),
    ([source("texto íntegro.")], [out("Texto íntegro.")]),
    ([source("• elemento")], [out("Elemento", kind="list_item")]),
    ([source("1. elemento")], [out("Elemento", kind="list_item", ordered=True)]),
    ([source("a) elemento")], [out("Elemento", kind="list_item", is_numbered=True)]),
    ([source("iv. elemento")], [out("Elemento", kind="list_item", is_numbered=True)]),
    ([source("1.1 elemento")], [out("Elemento", kind="list_item", is_numbered=True)]),
    ([source("Texto real")], [out("Resumen", kind="heading", level=2, generated=True), out("Texto real")]),
    ([source("Ana, Luis y Pedro.")], [out("Ana", kind="list_item"), out("Luis", kind="list_item"), out("Pedro.", kind="list_item")]),
    ([source("alfa; beta e ideas o dudas")], [out(t, kind="list_item") for t in ["Alfa", "Beta", "Ideas", "Dudas"]]),
    ([source("Nombre: Ana"), source("Nombre: Luis", "b2")], [table([
        [{"text": "Campo", "generated": True}, {"text": "Valor", "generated": True}],
        ["Nombre", "Ana"], ["Nombre", "Luis"],
    ])]),
    ([source("Nombre: Ana; Ciudad: Lima"), source("Nombre: Luis; Ciudad: Quito", "b2")], [table([
        ["Nombre", "Ciudad"], ["Ana", "Lima"], ["Luis", "Quito"],
    ])]),
    ([source("Ana | Lima"), source("Luis | Quito", "b2")], [table([["Ana", "Lima"], ["Luis", "Quito"]], header=False)]),
    ([source("Ana\tLima"), source("Luis\tQuito", "b2")], [table([["Ana", "Lima"], ["Luis", "Quito"]], header=False)]),
    ([source("Total $125.50 y 15%.")], [out("Total $125.50 y 15%.")]),
    ([source("Texto"), {"id": "k", "type": "keep", "xml": "<original/>"}, source("Fin", "b2")],
     [out("Texto"), {"type": "keep", "id": "k"}, out("Fin", "b2")]),
    ([], []),
])
def test_valid_cases(inputs, outputs):
    report = validate_chunk(inputs, outputs)
    assert report.ok, report.model_dump()
    assert not report.violations
    assert IntegrityReport.model_validate_json(report.model_dump_json()).ok


@pytest.mark.parametrize("glyph", ["•", "·", "◦", "▪", "-", "–", "*"])
def test_supported_glyphs(glyph):
    assert validate_chunk([source(f"{glyph} elemento")], [out("elemento", kind="list_item")]).ok


def test_configurable_bold_and_heading_limits():
    with override_settings(AI_MAX_BOLD_RATIO=1.0):
        assert validate_chunk([source("Texto real")], [out("Texto real", runs=[{"text": "Texto real", "bold": True}])]).ok
    with override_settings(AI_MAX_HEADING_WORDS=1):
        report = validate_chunk([source("Dos palabras")], [out("Dos palabras", kind="heading", level=1)])
        assert "HEADING_SHAPE" in {v.type for v in report.violations}
    with override_settings(AI_MAX_GENERATED_HEADING_WORDS=1):
        report = validate_chunk([source("Texto")], [out("Texto"), out("Dos palabras", kind="heading", level=2, generated=True)])
        assert "GENERATED_LENGTH" in {v.type for v in report.violations}


def test_retention_and_addition_thresholds_are_configurable():
    text = "uno dos tres cuatro cinco seis siete ocho nueve diez once doce trece catorce quince dieciseis diecisiete dieciocho diecinueve veinte"
    output = out(text.rsplit(" ", 1)[0], kind="list_item")
    assert validate_chunk([source(text)], [output]).ok
    with override_settings(AI_MIN_TOKEN_RETENTION=1.0):
        assert not validate_chunk([source(text)], [output]).ok
    output = out(text + " extra", kind="list_item")
    assert validate_chunk([source(text)], [output]).ok
    with override_settings(AI_MAX_ADDED_TOKEN_RATIO=0):
        assert not validate_chunk([source(text)], [output]).ok
    # Normal prose never gains invented text, even inside the numeric allowance.
    assert not validate_chunk([source(text)], [out(text + " extra")]).ok


def test_generated_defaults_and_schema_restrictions():
    assert HeadingOutBlock(level=1, runs=[{"text": "Título"}]).generated is False
    assert TableCell(text="Dato").generated is False
    for kind in ["paragraph", "list_item", "keep", "table"]:
        raw = out("Texto", kind=kind, generated=True)
        with pytest.raises(ValidationError):
            AIChunkOutput(chunk_id="c", blocks=[raw])


def test_missing_small_block_cannot_hide_behind_global_retention():
    sources = [source("contenido " * 100), source("indispensable", "b2")]
    assert not validate_chunk(sources, [out("contenido " * 100)]).ok


def test_repeated_tokens_still_preserve_exact_critical_data():
    text = ("contenido " * 200) + "$10"
    assert not validate_chunk([source(text)], [out(text.replace("$10", "$11"))]).ok


@pytest.mark.parametrize("currency", ["₱", "₿", "¤", "₴", "€"])
def test_unicode_currency_symbols_cannot_be_dropped(currency):
    assert not validate_chunk([source(f"Total {currency}10")], [out("Total 10")]).ok


def test_merged_table_cannot_hide_a_small_omitted_record_value():
    text = "contenido " * 100
    inputs = [source("Clave: " + text), source("Clave: indispensable", "b2")]
    outputs = [table([
        [{"text": "Campo", "generated": True}, {"text": "Valor", "generated": True}],
        ["Clave", text], ["Clave", ""],
    ])]
    report = validate_chunk(inputs, outputs)
    assert "SOURCE_CONTENT_OMITTED" in {v.type for v in report.violations}


def test_heading_bold_budget_is_checked_too():
    report = validate_chunk([source("Título")], [out(
        "Título", kind="heading", level=1, runs=[{"text": "Título", "bold": True}],
    )])
    assert "BOLD_RATIO" in {v.type for v in report.violations}


def test_generated_header_length_and_location():
    inputs = [source("Nombre: Ana"), source("Nombre: Luis", "b2")]
    rows = [[{"text": "Uno dos tres cuatro cinco seis siete", "generated": True},
             {"text": "Valor", "generated": True}], ["Nombre", "Ana"], ["Nombre", "Luis"]]
    report = validate_chunk(inputs, [table(rows)])
    assert "GENERATED_LENGTH" in {v.type for v in report.violations}
    report = validate_chunk(inputs, [table(rows, header=False)])
    assert "INVALID_SCHEMA" in {v.type for v in report.violations}


def test_permitted_structural_changes_produce_warnings():
    report = validate_chunk([source("• elemento")], [out("Elemento", kind="list_item")])
    assert report.ok and report.warnings


def test_empty_cell_runs_do_not_hide_missing_rendered_content():
    inputs = [source("Nombre: Ana"), source("Nombre: Luis", "b2")]
    outputs = [table([["Nombre", {"text": "Ana", "runs": []}], ["Nombre", "Luis"]], header=False)]
    assert not validate_chunk(inputs, outputs).ok
