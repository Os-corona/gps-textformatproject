"""Rebuilder v2: paquete original, listas nativas e integridad del resultado."""

from pathlib import Path

import pytest
from docx import Document
from docx.enum.style import WD_STYLE_TYPE
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from docx.oxml.ns import qn
from lxml import etree
from pydantic import ValidationError

from common.document_schema import AIChunkOutput, CalloutOutBlock, KeepOutBlock
from common.integrity import tokenize, validate_tokens
from docx_engine import rebuilder
from docx_engine.extractor import extract_document
from docx_engine.rebuilder import DocumentIntegrityError, rebuild_document


FIXTURES = Path(__file__).parent / "fixtures"


def paragraph(text, **kwargs):
    return {"type": "paragraph", "runs": [{"text": text}], **kwargs}


def item(text, level=0, ordered=True, **kwargs):
    return {"type": "list_item", "level": level, "ordered": ordered, "runs": [{"text": text}], **kwargs}


def numbering(paragraph):
    properties = paragraph._p.pPr.numPr
    return properties.numId.val, properties.ilvl.val


def test_keep_preserves_original_xml_images_and_relationships_without_temp_files(tmp_path, monkeypatch):
    from docx_engine import extractor

    path = FIXTURES / "04_tabla_imagen.docx"
    original_bytes = path.read_bytes()
    original = Document(path)
    di = extract_document(path).model_dump()
    # El XML enviado en un keep no sustituye al original referenciado.
    di["blocks"][4]["xml"] = "<forged/>"
    image_directory = tmp_path / "images"
    monkeypatch.setattr(extractor, "IMG_DIR", str(image_directory))
    result = rebuild_document(path, di)

    for index in (1, 4):
        assert etree.tostring(result.element.body[index]) == etree.tostring(original.element.body[index])
    for blip in result.element.body.xpath(".//a:blip"):
        rid = blip.get(qn("r:embed"))
        assert result.part.related_parts[rid].blob == original.part.related_parts[rid].blob
        assert result.part.rels[rid].target_ref == original.part.rels[rid].target_ref
    assert not image_directory.exists()
    assert path.read_bytes() == original_bytes
    assert len(result.element.body.findall(qn("w:sectPr"))) == 1


def test_clone_preserves_headers_footers_styles_and_caller_document():
    original = Document()
    original.add_paragraph("Texto original")
    original.sections[0].header.paragraphs[0].text = "Encabezado original"
    original.sections[0].footer.paragraphs[0].text = "Pie original"
    original.styles.add_style("Estilo propio", WD_STYLE_TYPE.PARAGRAPH)
    original_xml = original.element.xml

    result = rebuild_document(original, [paragraph("Texto reconstruido")])

    assert original.element.xml == original_xml
    assert original.paragraphs[0].text == "Texto original"
    assert result.paragraphs[0].text == "Texto reconstruido"
    assert result.sections[0].header.paragraphs[0].text == "Encabezado original"
    assert result.sections[0].footer.paragraphs[0].text == "Pie original"
    assert "Estilo propio" in result.styles


@pytest.mark.parametrize(("kind", "style"), [("quote", "Quote"), ("note", "Intense Quote"), ("warning", "Intense Quote")])
def test_heading_paragraph_and_callout_styles_are_applied_and_created(kind, style):
    original = Document()
    original.styles[style].delete()
    blocks = [
        {"type": "heading", "level": level, "runs": [{"text": f"Título {level}"}]}
        for level in range(4)
    ] + [paragraph("Cuerpo"), {"type": "callout", "kind": kind, "runs": [{"text": "Cita"}]}]
    result = rebuild_document(original, {"blocks": blocks})
    assert [p.style.name for p in result.paragraphs] == [
        "Title", "Heading 1", "Heading 2", "Heading 3", "Normal", style,
    ]
    assert result.styles[style].type == WD_STYLE_TYPE.PARAGRAPH


def test_runs_preserve_boolean_overrides_but_do_not_apply_font_size_or_color():
    blocks = [{"type": "paragraph", "runs": [
        {"text": "Uno", "bold": True, "italic": False, "underline": True,
         "font": "Arial", "size": 22, "color": "FF0000"},
        {"text": " dos", "bold": False, "italic": True, "underline": False},
        {"text": " tres"},
    ]}]
    result = rebuild_document(Document(), blocks)
    first, second, third = result.paragraphs[0].runs
    assert (first.bold, first.italic, first.underline) == (True, False, True)
    assert (second.bold, second.italic, second.underline) == (False, True, False)
    assert (third.bold, third.italic, third.underline) == (None, None, None)
    for run in result.paragraphs[0].runs:
        assert run.font.name is None
        assert run.font.size is None
        assert run.font.color.rgb is None


def test_native_lists_use_all_levels_and_leave_original_definitions_unchanged():
    original = Document()
    root = original.part.numbering_part.element
    original_definitions = [etree.tostring(element) for element in root]
    blocks = [item(f"Nivel {level}", level) for level in range(9)]
    blocks += [paragraph("Separación"), item("Viñeta", 2, False)]
    result = rebuild_document(original, blocks)

    assert [numbering(p)[1] for p in result.paragraphs[:9]] == list(range(9))
    assert len({numbering(p)[0] for p in result.paragraphs[:9]}) == 1
    result_root = result.part.numbering_part.element
    for definition in original_definitions:
        assert definition in [etree.tostring(element) for element in result_root]
    for paragraph_index, fmt in ((0, "decimal"), (10, "bullet")):
        num_id, _ = numbering(result.paragraphs[paragraph_index])
        num = result_root.num_having_numId(num_id)
        abstract = result_root.xpath(f'./w:abstractNum[@w:abstractNumId="{num.abstractNumId.val}"]')[0]
        assert len(abstract.findall(qn("w:lvl"))) == 9
        formats = abstract.findall("./" + qn("w:lvl") + "/" + qn("w:numFmt"))
        assert {node.get(qn("w:val")) for node in formats} == {fmt}


def test_ordered_lists_restart_and_resume_after_nested_bullets():
    blocks = [
        item("Primero"), item("Viñeta anidada", 1, False), item("Segundo"),
        paragraph("Otra lista"), item("Nuevo primero"),
        item("Reinicio explícito", restart=True), item("Siguiente"),
        item("Lista distinta", list_id="otra"),
    ]
    result = rebuild_document(Document(), blocks)
    ids = [numbering(p)[0] if p._p.pPr.numPr is not None else None for p in result.paragraphs]
    assert ids[0] == ids[2]
    assert len({ids[0], ids[4], ids[5], ids[7]}) == 4
    assert ids[5] == ids[6]
    root = result.part.numbering_part.element
    for num_id in (ids[0], ids[4], ids[5], ids[7]):
        overrides = root.num_having_numId(num_id).xpath("./w:lvlOverride/w:startOverride/@w:val")
        assert overrides == ["1"] * 9


def test_existing_multilevel_definitions_are_reused():
    first = rebuild_document(Document(), [item("Número"), item("Viñeta", ordered=False)])
    before = len(first.part.numbering_part.element.findall(qn("w:abstractNum")))
    second = rebuild_document(first, [item("Otro número"), item("Otra viñeta", ordered=False)])
    assert len(second.part.numbering_part.element.findall(qn("w:abstractNum"))) == before


def test_numbering_part_is_created_for_packages_without_numbering():
    original = Document()
    relation = next(rel for rel in original.part.rels.values() if rel.reltype == RT.NUMBERING)
    original.part.drop_rel(relation.rId)
    result = rebuild_document(original, [item("Primero"), item("Viñeta", ordered=False)])
    assert result.part.numbering_part.element.findall(qn("w:abstractNum"))
    assert numbering(result.paragraphs[0])[1] == 0
    assert numbering(result.paragraphs[1])[1] == 0


def test_new_tables_preserve_spans_runs_header_and_body_order():
    blocks = [paragraph("Antes"), {"type": "table", "rows": [
        [{"text": "Encabezado combinado", "h_span": 2}, {"text": "Última"}],
        [{"runs": [{"text": "Dato", "underline": True}]}, {"text": "Segundo"}, {"text": "Tercero"}],
    ]}, paragraph("Después")]
    result = rebuild_document(Document(), blocks)
    table = result.tables[0]
    assert [child.tag for child in result.element.body] == [qn(name) for name in ("w:p", "w:tbl", "w:p", "w:sectPr")]
    assert len(table.rows[0]._tr.tc_lst) == 2
    assert table.cell(0, 0)._tc.tcPr.gridSpan.val == 2
    assert table.rows[0]._tr.trPr.find(qn("w:tblHeader")) is not None
    assert table.rows[1]._tr.trPr.find(qn("w:tblHeader")) is None
    assert table.rows[1]._tr.trPr.find(qn("w:cantSplit")) is not None
    assert table.cell(1, 0).paragraphs[0].runs[0].underline is True
    assert [p.text for p in result.paragraphs] == ["Antes", "Después"]


def test_result_tokens_keep_accented_words_numbers_and_run_boundaries():
    blocks = [{"type": "paragraph", "runs": [{"text": "Ár"}, {"text": "bol 123 "}, {"text": "México"}]}]
    result = rebuild_document(Document(), blocks)
    assert result.paragraphs[0].text == "Árbol 123 México"
    assert tokenize(result.paragraphs[0].text) == ["Árbol", "123", "México"]
    assert validate_tokens("Árbol 123 México", result.paragraphs[0].text).is_valid
    assert not validate_tokens("Árbol 123 México", "árbol 123 México").is_valid
    assert not validate_tokens("Árbol 123 México", "123 Árbol México").is_valid


def test_serialized_result_is_validated_and_text_corruption_is_rejected(monkeypatch):
    original_add = rebuilder._add_structured_runs

    def corrupt(paragraph, runs):
        original_add(paragraph, runs)
        paragraph.runs[0].text = "Alterado"

    monkeypatch.setattr(rebuilder, "_add_structured_runs", corrupt)
    with pytest.raises(DocumentIntegrityError) as error:
        rebuild_document(Document(), [paragraph("Original")])
    assert not error.value.report.is_valid
    assert error.value.report.metadata["first_mismatch"] == 0


@pytest.mark.parametrize("mutation", ["missing", "duplicate", "reordered", "unknown"])
def test_missing_duplicate_reordered_or_unknown_keep_is_rejected(mutation):
    original = Document()
    original.add_table(rows=1, cols=1).cell(0, 0).text = "Primera"
    original.add_table(rows=1, cols=1).cell(0, 0).text = "Segunda"
    blocks = [{"type": "keep", "src": ["b0"]}, {"type": "keep", "src": ["b1"]}]
    if mutation == "missing":
        blocks.pop()
    elif mutation == "duplicate":
        blocks.append(blocks[0])
    elif mutation == "reordered":
        blocks.reverse()
    else:
        blocks.append({"type": "keep", "src": ["b404"]})
    with pytest.raises(ValueError):
        rebuild_document(original, blocks)


def test_keep_can_group_multiple_original_ids_and_final_section_is_not_duplicated():
    original = Document()
    original.add_table(rows=1, cols=1).cell(0, 0).text = "Tabla"
    original.add_paragraph()
    result = rebuild_document(original, [KeepOutBlock(src=["b0", "b1", "b2"])])
    assert len(result.tables) == 1
    assert len(result.sections) == 1
    assert len(result.element.body) == 3


@pytest.mark.parametrize("block", [
    {"type": "heading", "level": -1, "runs": [{"text": "Inválido"}]},
    {"type": "list_item", "level": 9, "runs": [{"text": "Inválido"}]},
    {"type": "table", "rows": [[{"text": "A"}], [{"text": "B"}, {"text": "C"}]]},
    {"type": "paragraph", "runs": []},
    {"type": "unknown"},
])
def test_invalid_structured_blocks_are_rejected(block):
    with pytest.raises(ValidationError):
        rebuild_document(Document(), [block])


def test_ai_output_models_preserve_src_callout_keep_and_ordered_alias():
    output = AIChunkOutput(chunk_id="c1", blocks=[
        {"type": "heading", "level": 0, "src": ["b0"], "runs": [{"text": "Título"}]},
        {"type": "list_item", "ordered": True, "src": ["b1"], "runs": [{"text": "Elemento"}]},
        {"type": "callout", "kind": "note", "src": ["b2"], "runs": [{"text": "Nota"}]},
    ])
    restored = AIChunkOutput.model_validate_json(output.model_dump_json())
    assert restored.blocks[0].src == ["b0"]
    assert restored.blocks[1].is_numbered
    assert isinstance(restored.blocks[2], CalloutOutBlock)
    assert [p.text for p in rebuild_document(Document(), restored).paragraphs] == ["Título", "Elemento", "Nota"]
    with pytest.raises(ValidationError):
        KeepOutBlock()


def test_empty_paragraph_keeps_can_be_omitted_or_collapsed():
    original = Document()
    original.add_paragraph("Título")
    original.add_paragraph("")
    original.add_paragraph("")
    original.add_paragraph("Cuerpo")
    original.add_table(rows=1, cols=1).cell(0, 0).text = "Dato"

    di = extract_document(original)
    # 1) Omitir empty_paragraph (b1, b2) conservando la tabla opaca (b4) es válido
    without_blanks = [
        {"type": "heading", "level": 1, "src": ["b0"], "runs": [{"text": "Título"}]},
        {"type": "paragraph", "src": ["b3"], "runs": [{"text": "Cuerpo"}]},
        {"type": "keep", "src": ["b4"]},
    ]
    rebuilt = rebuild_document(original, without_blanks)
    assert [p.text for p in rebuilt.paragraphs] == ["Título", "Cuerpo"]
    assert len(rebuilt.tables) == 1

    # 2) collapse_empty_paragraphs=True limpia empty_paragraph automáticamente sobre el DI completo
    collapsed = rebuild_document(original, di, collapse_empty_paragraphs=True)
    assert [p.text for p in collapsed.paragraphs] == ["Título", "Cuerpo"]
    assert len(collapsed.tables) == 1


def test_structured_table_header_row_flag_and_editorial_layout():
    table_with_header = {
        "type": "table",
        "header_row": True,
        "rows": [
            [{"text": "Clave"}, {"text": "Valor"}],
            [{"text": "Ventas"}, {"text": "15%"}],
        ],
    }
    table_without_header = {
        "type": "table",
        "header_row": False,
        "rows": [
            [{"text": "A"}, {"text": "1"}],
            [{"text": "B"}, {"text": "2"}],
        ],
    }

    result = rebuild_document(Document(), [table_with_header, table_without_header])
    assert len(result.tables) == 2

    t1, t2 = result.tables
    assert t1.rows[0]._tr.xpath("./w:trPr/w:tblHeader")
    assert not t2.rows[0]._tr.xpath("./w:trPr/w:tblHeader")

    for tbl in (t1, t2):
        tbl_w = tbl._tbl.xpath("./w:tblPr/w:tblW")
        assert tbl_w and tbl_w[0].get(qn("w:w")) == "5000" and tbl_w[0].get(qn("w:type")) == "pct"
        assert tbl._tbl.xpath("./w:tblPr/w:tblCellMar")
        for row in tbl.rows:
            assert row._tr.xpath("./w:trPr/w:cantSplit")

