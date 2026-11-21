"""Contrato del extractor v2, preservación opaca y compatibilidad de /extract/."""

from io import BytesIO
from pathlib import Path
from unittest.mock import patch

import pytest
from docx import Document
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.text import WD_UNDERLINE
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn
from docx.shared import Cm, Pt
from lxml import etree

from common.document_schema import DI, SourceBlock
from docx_engine import extractor
from docx_engine.extractor import extract_document, extract_structure
from docx_engine.rebuilder import rebuild_from_structure


FIXTURES = Path(__file__).parent / "fixtures"


def stream(document):
    buffer = BytesIO()
    document.save(buffer)
    buffer.seek(0)
    return buffer


@pytest.mark.parametrize("path", sorted(FIXTURES.glob("*.docx")), ids=lambda p: p.stem)
def test_ids_cover_every_body_child_and_are_repeatable(path):
    original = path.read_bytes()
    first = extract_document(path)
    second = extract_document(path)
    body = Document(path).element.body

    assert all(isinstance(block, SourceBlock) for block in first.blocks)
    assert [block.id for block in first.blocks] == [f"b{i}" for i in range(len(body))]
    assert first == second == DI.model_validate_json(first.model_dump_json())
    assert first.stats.total_blocks == len(body)
    assert first.stats.text_blocks == sum(block.type == "paragraph" for block in first.blocks)
    assert first.stats.opaque_blocks == sum(block.type == "keep" for block in first.blocks)
    assert first.stats.total_blocks == first.stats.text_blocks + first.stats.opaque_blocks
    assert first.stats.opaque_reasons == {
        block.id: block.opaque_reasons for block in first.blocks if block.type == "keep"
    }
    assert path.read_bytes() == original


def test_fixture_lists_distinguishes_glyphs_manual_numbers_and_indents():
    di = extract_document(FIXTURES / "05_listas.docx")
    glyphs = [b for b in di.blocks if b.hints and b.hints.starts_with_glyph]
    numbers = [b for b in di.blocks if b.hints and b.hints.manual_numbering]

    assert len(glyphs) == 8
    assert len(numbers) == 10
    assert [di.blocks[i].hints.indent_level for i in (2, 3, 4)] == [1, 2, 3]
    assert [di.blocks[i].hints.indent_cm for i in (2, 3, 4)] == pytest.approx([1.905, 2.54, 3.175])
    assert all(not b.hints.is_native_list for b in glyphs + numbers)
    assert all(not b.hints.manual_numbering for b in glyphs)


def test_fixture_false_headings_have_relative_size_signal():
    di = extract_document(FIXTURES / "02_headings_mixto.docx")
    by_text = {b.text: b for b in di.blocks}
    for text in ("1. RESUMEN", "Observaciones importantes", "Anexos"):
        heading = by_text[text]
        assert heading.type == "paragraph"
        assert heading.hints.style_name == "Normal"
        assert heading.hints.size_ratio > 1.2
    assert by_text["1. RESUMEN"].hints.manual_numbering
    assert by_text["1. RESUMEN"].hints.words == 2


@pytest.mark.parametrize(("name", "expected"), [
    ("04_tabla_imagen.docx", {
        "b1": ["table"], "b2": ["empty_paragraph"], "b4": ["image"],
        "b5": ["empty_paragraph"], "b6": ["section_properties"],
    }),
    ("06_secciones.docx", {
        "b3": ["section_break"], "b7": ["section_break"],
        "b11": ["empty_paragraph"], "b12": ["section_properties"],
    }),
])
def test_fixture_opaque_blocks_preserve_exact_xml(name, expected):
    path = FIXTURES / name
    di = extract_document(path)
    body = Document(path).element.body
    assert di.stats.opaque_reasons == expected
    for index, block in enumerate(di.blocks):
        if block.type == "keep":
            assert block.xml == etree.tostring(body[index], encoding="unicode", with_tail=False)


def test_v2_does_not_extract_images_to_disk(tmp_path, monkeypatch):
    image_dir = tmp_path / "images"
    monkeypatch.setattr(extractor, "IMG_DIR", str(image_dir))
    di = extract_document(FIXTURES / "04_tabla_imagen.docx")
    assert "image" in di.stats.opaque_reasons["b4"]
    assert not image_dir.exists()


def test_base_size_uses_character_weight_not_run_count_and_maximum_run_size():
    doc = Document()
    # Diez runs grandes pesan menos que un solo run de cuerpo largo.
    for _ in range(10):
        doc.add_paragraph().add_run("X").font.size = Pt(24)
    body = doc.add_paragraph()
    body.add_run("Texto de cuerpo suficientemente largo. " * 3).font.size = Pt(10)
    mixed = doc.add_paragraph()
    mixed.add_run("Texto ").font.size = Pt(10)
    mixed.add_run("mayor").font.size = Pt(18)

    di = extract_document(stream(doc))
    assert di.base_font_size == 10
    assert di.blocks[0].hints.size_ratio == 2.4
    assert di.blocks[10].hints.size_ratio == 1.0
    assert di.blocks[11].hints.size_ratio == 1.8


def test_inherited_size_bold_and_underline_and_explicit_overrides():
    doc = Document()
    doc.styles["Normal"].font.size = Pt(10)
    doc.add_paragraph("Cuerpo base. " * 20)
    parent = doc.styles.add_style("Parent heading", WD_STYLE_TYPE.PARAGRAPH)
    parent.font.size = Pt(18)
    parent.font.bold = True
    parent.font.underline = True
    child = doc.styles.add_style("Child heading", WD_STYLE_TYPE.PARAGRAPH)
    child.base_style = parent
    paragraph = doc.add_paragraph("Título heredado", style=child)
    paragraph.add_run(" sin negrita").bold = False
    paragraph.runs[-1].underline = False

    di = extract_document(stream(doc))
    heading = di.blocks[1]
    assert di.base_font_size == 10
    assert heading.hints.size_ratio == 1.8
    assert not heading.hints.all_bold
    assert heading.runs[0].underline is True
    assert heading.runs[1].underline is False


def test_character_style_and_document_defaults_resolve_font_size():
    doc = Document()
    defaults = doc.styles.element.xpath("./w:docDefaults/w:rPrDefault/w:rPr/w:sz")[0]
    defaults.set(qn("w:val"), "20")
    doc.add_paragraph("Texto base. " * 20)
    character = doc.styles.add_style("Large character", WD_STYLE_TYPE.CHARACTER)
    character.font.size = Pt(20)
    character.font.bold = True
    paragraph = doc.add_paragraph()
    paragraph.add_run("Grande").style = character

    di = extract_document(stream(doc))
    assert di.base_font_size == 10
    assert di.blocks[1].hints.size_ratio == 2
    assert di.blocks[1].hints.all_bold


def test_size_ratio_includes_whitespace_runs_but_all_bold_ignores_them():
    doc = Document()
    doc.add_paragraph().add_run("Cuerpo base. " * 10).font.size = Pt(10)
    p = doc.add_paragraph()
    text = p.add_run("Título")
    text.font.size = Pt(16)
    text.bold = True
    p.add_run(" ").font.size = Pt(20)

    hints = extract_document(stream(doc)).blocks[1].hints
    assert hints.size_ratio == 2
    assert hints.all_bold


@pytest.mark.parametrize(("text", "numbered", "glyph"), [
    ("1. Primero", True, False), ("1.2. Subtema", True, False),
    ("1.2 Subtema", True, False),
    ("(3) Tercero", True, False), ("a) Opción", True, False),
    ("IV. Parte", True, False), ("2026 fue un año", False, False),
    ("3.14", False, False), ("• Elemento", False, True),
    ("•Elemento", False, True),
    ("  ◦ Elemento", False, True), ("– Elemento", False, True),
    ("-5 grados", False, False),
])
def test_manual_list_signals(text, numbered, glyph):
    doc = Document()
    doc.add_paragraph(text)
    hints = extract_document(stream(doc)).blocks[0].hints
    assert hints.manual_numbering is numbered
    assert hints.starts_with_glyph is glyph
    assert hints.words == len(text.split())
    assert hints.ends_with_period is text.rstrip().endswith(".")


def test_native_numbering_is_inherited_and_can_be_disabled():
    doc = Document()
    doc.add_paragraph("Lista nativa", style="List Number")
    nested = doc.add_paragraph("Anidada", style="List Number")
    nested._p.get_or_add_pPr().get_or_add_numPr().get_or_add_ilvl().val = 2
    cancelled = doc.add_paragraph("Ya no es lista", style="List Number")
    cancelled._p.get_or_add_pPr().get_or_add_numPr().get_or_add_numId().val = 0

    di = extract_document(stream(doc))
    assert di.blocks[0].hints.is_native_list
    assert di.blocks[0].hints.is_numbered
    assert di.blocks[1].hints.is_native_list
    assert di.blocks[1].hints.list_level == 2
    assert not di.blocks[2].hints.is_native_list


@pytest.mark.parametrize(("xml", "reason"), [
    ('<w:r><w:drawing/></w:r>', "drawing"),
    ('<w:r><w:pict><v:imagedata xmlns:v="urn:schemas-microsoft-com:vml"/></w:pict></w:r>', "image"),
    ('<w:fldSimple w:instr="PAGE"/>', "field"),
    ('<w:r><w:fldChar w:fldCharType="begin"/></w:r>', "field"),
    ('<w:r><w:footnoteReference w:id="1"/></w:r>', "footnote"),
    ('<w:r><w:endnoteReference w:id="1"/></w:r>', "footnote"),
    ('<w:hyperlink><w:r><w:t>Enlace</w:t></w:r></w:hyperlink>', "hyperlink"),
    ('<w:ins w:id="1"><w:r><w:t>Inserción</w:t></w:r></w:ins>', "tracked_change"),
    ('<w:del w:id="2"><w:r><w:delText>Borrado</w:delText></w:r></w:del>', "tracked_change"),
    ('<w:r><w:rPr><w:rPrChange w:id="3"/></w:rPr></w:r>', "tracked_change"),
    ('<w:pPr><w:sectPr/></w:pPr>', "section_break"),
    ('<w:sdt><w:sdtContent/></w:sdt>', "unknown_element"),
    ('<w:r><w:unsupported/></w:r>', "unknown_element"),
])
def test_sensitive_paragraphs_are_opaque_even_when_they_also_have_text(xml, reason):
    doc = Document()
    paragraph = doc.add_paragraph("Texto que no debe reescribirse")
    paragraph._p.append(parse_xml(f'<w:p {nsdecls("w")}>{xml}</w:p>')[0])
    di = extract_document(stream(doc))

    block = di.blocks[0]
    assert block.type == "keep"
    assert reason in block.opaque_reasons
    assert block.runs is None
    assert block.xml is not None
    assert reason in di.stats.opaque_reasons["b0"]


def test_field_spanning_multiple_paragraphs_protects_the_entire_range():
    doc = Document()
    for text, kind in (("Inicio", "begin"), ("Resultado", None), ("Final", "end"), ("Normal", None)):
        p = doc.add_paragraph(text)
        if kind:
            field = OxmlElement("w:fldChar")
            field.set(qn("w:fldCharType"), kind)
            p.add_run()._r.append(field)

    di = extract_document(stream(doc))
    assert all(b.opaque_reasons == ["field"] for b in di.blocks[:3])
    assert di.blocks[3].type == "paragraph"


def test_unknown_body_children_and_empty_paragraphs_do_not_shift_ids():
    doc = Document()
    doc.add_paragraph()
    doc.element.body.insert(1, OxmlElement("w:customXml"))
    doc.add_paragraph("Texto final")

    di = extract_document(stream(doc))
    assert di.blocks[0].opaque_reasons == ["empty_paragraph"]
    assert di.blocks[1].opaque_reasons == ["unknown_element"]
    assert di.blocks[2].id == "b2"
    assert di.blocks[2].text == "Texto final"
    assert di.blocks[3].opaque_reasons == ["section_properties"]


def test_tracked_change_wrapping_a_body_paragraph_is_preserved():
    doc = Document()
    wrapper = parse_xml(f'<w:ins {nsdecls("w")} w:id="1"><w:p><w:r><w:t>Nuevo</w:t></w:r></w:p></w:ins>')
    doc.element.body.insert(0, wrapper)

    di = extract_document(stream(doc))
    assert di.blocks[0].type == "keep"
    assert di.blocks[0].opaque_reasons == ["tracked_change"]
    assert "Nuevo" in di.blocks[0].xml


def test_indent_uses_inherited_left_and_modern_start_attributes():
    doc = Document()
    style = doc.styles.add_style("Indented", WD_STYLE_TYPE.PARAGRAPH)
    style.paragraph_format.left_indent = Cm(1)
    doc.add_paragraph("Primer nivel", style=style)
    p = doc.add_paragraph("Segundo nivel", style=style)
    ind = OxmlElement("w:ind")
    ind.set(qn("w:start"), "1440")
    ind.set(qn("w:left"), "720")
    p._p.get_or_add_pPr().append(ind)

    di = extract_document(stream(doc))
    assert [b.hints.indent_level for b in di.blocks[:2]] == [1, 2]
    assert di.blocks[0].hints.indent_cm == pytest.approx(1, abs=0.001)
    assert di.blocks[1].hints.indent_cm == 2.54


def test_adapter_uses_v2_and_preserves_underline_through_rebuild():
    doc = Document()
    p = doc.add_paragraph()
    p.add_run("Subrayado").underline = WD_UNDERLINE.DOUBLE
    p.add_run(" sin subrayado").underline = False
    p.add_run(" normal")
    with patch.object(extractor, "extract_document", wraps=extract_document) as v2:
        blocks = extract_structure(stream(doc))
    v2.assert_called_once()
    assert [r["underline"] for r in blocks[0]["runs"]] == [True, False, None]
    rebuilt = Document(stream(rebuild_from_structure(blocks)))
    assert [r.underline for r in rebuilt.paragraphs[0].runs] == [True, False, None]


def test_extract_endpoint_still_returns_json_serializable_legacy_blocks():
    from django.core.files.uploadedfile import SimpleUploadedFile
    from rest_framework.test import APIRequestFactory
    from api.views import extract_text_view

    uploaded = SimpleUploadedFile("04.docx", (FIXTURES / "04_tabla_imagen.docx").read_bytes())
    response = extract_text_view(APIRequestFactory().post("/api/documents/extract/", {"file": uploaded}))
    response.render()
    assert response.status_code == 200
    assert response.data["total_blocks"] == len(response.data["blocks"])
    assert any(b["type"] == "table" and b["rows"] for b in response.data["blocks"])
    assert any(b.get("has_inline_image") for b in response.data["blocks"])


def test_empty_document_has_a_valid_baseline_and_preserves_final_section():
    di = extract_document(stream(Document()))
    assert di.base_font_size > 0
    assert di.stats.text_blocks == 0
    assert di.stats.opaque_blocks == di.stats.total_blocks == 1
    assert di.blocks[0].opaque_reasons == ["section_properties"]
    assert di.blocks[0].keep_kind == "section_break"


def test_enriched_hints_caps_alignment_blanks_tabs_kv_and_keep_kind():
    from docx.enum.text import WD_ALIGN_PARAGRAPH

    doc = Document()
    doc.add_paragraph("")
    title = doc.add_paragraph("RESUMEN EJECUTIVO")
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.add_paragraph("")
    doc.add_paragraph("")
    kv = doc.add_paragraph("Región Norte: incremento del 15%")
    kv.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    tabbed = doc.add_paragraph("Col A\tCol B\tCol C")
    doc.add_table(rows=1, cols=2)

    di = extract_document(stream(doc))

    assert di.blocks[0].type == "keep"
    assert di.blocks[0].keep_kind == "empty"

    title_block = di.blocks[1]
    assert title_block.hints.is_all_caps is True
    assert title_block.hints.alignment == "center"
    assert title_block.hints.blank_lines_before == 1
    assert title_block.hints.blank_lines_after == 2
    assert title_block.hints.has_key_value_pattern is False

    kv_block = di.blocks[4]
    assert kv_block.hints.is_all_caps is False
    assert kv_block.hints.alignment == "justify"
    assert kv_block.hints.blank_lines_before == 2
    assert kv_block.hints.blank_lines_after == 0
    assert kv_block.hints.has_key_value_pattern is True

    tab_block = di.blocks[5]
    assert tab_block.hints.tab_count == 2

    table_block = di.blocks[6]
    assert table_block.type == "keep"
    assert table_block.keep_kind == "table"

