"""
Pruebas para templates_engine v2 (S3T12).
Verifica los módulos headings.py, paragraphs.py, lists.py, tables.py y page_numbers.py
sobre documentos generados por el rebuilder v2 a partir de bloques de estructura.
"""

from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from django.test import SimpleTestCase

from docx_engine.rebuilder import rebuild_from_structure
from templates_engine.config import (
    TemplateConfig,
    load_preset,
    ParagraphConfig,
    HeadingsConfig,
    HeadingItemConfig,
    ListsConfig,
    TablesConfig,
    CalloutConfig,
    AIConfig,
)
from templates_engine.headings import apply_headings
from templates_engine.paragraphs import apply_paragraphs
from templates_engine.lists import apply_lists
from templates_engine.tables import apply_tables
from templates_engine.page_numbers import apply_page_numbers
from templates_engine.applier import apply_template


def create_sample_structure_blocks():
    """Genera una estructura representativa de bloques para probar el rebuilder v2."""
    return [
        {
            "type": "paragraph",
            "style_name": "Title",
            "text": "Título del Documento",
            "runs": [{"text": "Título del Documento"}],
        },
        {
            "type": "paragraph",
            "style_name": "Heading 1",
            "text": "1. Introducción General",
            "runs": [{"text": "1. Introducción General"}],
        },
        {
            "type": "paragraph",
            "style_name": "Normal",
            "text": "Este es el primer párrafo de cuerpo que debe recibir sangría y alineación.",
            "runs": [{"text": "Este es el primer párrafo de cuerpo que debe recibir sangría y alineación."}],
        },
        {
            "type": "paragraph",
            "style_name": "Heading 2",
            "text": "1.1 Subtema Específico",
            "runs": [{"text": "1.1 Subtema Específico"}],
        },
        {
            "type": "paragraph",
            "style_name": "Quote",
            "text": "Esta es una cita destacada que debe formatearse como callout.",
            "runs": [{"text": "Esta es una cita destacada que debe formatearse como callout."}],
        },
        {
            "type": "paragraph",
            "style_name": "List Bullet",
            "text": "Primer elemento de lista con viñeta.",
            "runs": [{"text": "Primer elemento de lista con viñeta."}],
            "list_info": {"is_list": True, "is_numbered": False, "level": 0},
        },
        {
            "type": "paragraph",
            "style_name": "List Number",
            "text": "Primer elemento de lista numerada nivel 1.",
            "runs": [{"text": "Primer elemento de lista numerada nivel 1."}],
            "list_info": {"is_list": True, "is_numbered": True, "level": 1},
        },
        {
            "type": "table",
            "rows": [
                [{"text": "Encabezado Col 1", "h_span": 1}, {"text": "Encabezado Col 2", "h_span": 1}],
                [{"text": "Fila 1 Val 1", "h_span": 1}, {"text": "Fila 1 Val 2", "h_span": 1}],
                [{"text": "Fila 2 Val 1", "h_span": 1}, {"text": "Fila 2 Val 2", "h_span": 1}],
            ],
        },
    ]


class HeadingsModuleTests(SimpleTestCase):
    def test_headings_keep_with_next_and_formatting(self):
        blocks = create_sample_structure_blocks()
        doc = rebuild_from_structure(blocks)

        h_cfg = HeadingsConfig(
            h1=HeadingItemConfig(size_pt=14, bold=True, align="center", space_before_pt=18, space_after_pt=6, color="1F497D"),
            h2=HeadingItemConfig(size_pt=12, bold=True, align="left", space_before_pt=12, space_after_pt=4),
            title=HeadingItemConfig(size_pt=18, bold=True, align="center"),
        )
        apply_headings(doc, headings_config=h_cfg)

        for p in doc.paragraphs:
            name = p.style.name if p.style else ""
            if "Heading 1" in name:
                self.assertTrue(p.paragraph_format.keep_with_next)
                self.assertEqual(p.alignment, WD_ALIGN_PARAGRAPH.CENTER)
                self.assertEqual(p.paragraph_format.space_before, Pt(18))
                self.assertEqual(p.paragraph_format.space_after, Pt(6))
                self.assertTrue(p.runs[0].bold)
                self.assertEqual(p.runs[0].font.size, Pt(14))
                self.assertEqual(p.runs[0].font.color.rgb, RGBColor(0x1F, 0x49, 0x7D))
            elif "Heading 2" in name:
                self.assertTrue(p.paragraph_format.keep_with_next)
                self.assertEqual(p.alignment, WD_ALIGN_PARAGRAPH.LEFT)
                self.assertTrue(p.runs[0].bold)
                self.assertEqual(p.runs[0].font.size, Pt(12))
            elif "Title" in name:
                self.assertTrue(p.paragraph_format.keep_with_next)
                self.assertEqual(p.alignment, WD_ALIGN_PARAGRAPH.CENTER)


class ParagraphsModuleTests(SimpleTestCase):
    def test_paragraphs_indent_alignment_and_callout(self):
        blocks = create_sample_structure_blocks()
        doc = rebuild_from_structure(blocks)

        p_cfg = ParagraphConfig(alignment="justify", first_line_indent_cm=1.27, space_after_pt=6.0)
        c_cfg = CalloutConfig(italic=True, left_indent_cm=2.0, fill="F2F2F2")

        apply_paragraphs(doc, paragraph_config=p_cfg, callout_config=c_cfg)

        normal_found = False
        quote_found = False

        for p in doc.paragraphs:
            name = p.style.name if p.style else ""
            if name == "Normal":
                normal_found = True
                self.assertEqual(p.alignment, WD_ALIGN_PARAGRAPH.JUSTIFY)
                expected_indent = Inches(1.27 / 2.54)
                self.assertAlmostEqual(p.paragraph_format.first_line_indent.inches, expected_indent.inches, places=2)
                self.assertEqual(p.paragraph_format.space_after, Pt(6.0))
            elif "Quote" in name:
                quote_found = True
                self.assertTrue(p.runs[0].italic)
                expected_left = Inches(2.0 / 2.54)
                self.assertAlmostEqual(p.paragraph_format.left_indent.inches, expected_left.inches, places=2)
                # Shading XML
                self.assertTrue("F2F2F2" in p._p.xml)
            elif name.startswith("Heading"):
                # Los encabezados no deben recibir sangría de primera línea del cuerpo
                self.assertIsNone(p.paragraph_format.first_line_indent)

        self.assertTrue(normal_found)
        self.assertTrue(quote_found)


class ListsModuleTests(SimpleTestCase):
    def test_lists_indentation_per_level(self):
        blocks = create_sample_structure_blocks()
        doc = rebuild_from_structure(blocks)

        l_cfg = ListsConfig(indent_cm_per_level=1.27)
        apply_lists(doc, lists_config=l_cfg)

        list_found = False
        for p in doc.paragraphs:
            name = p.style.name if p.style else ""
            if "List" in name or p._p.xpath("./w:pPr/w:numPr"):
                list_found = True
                self.assertIsNotNone(p.paragraph_format.left_indent)
                self.assertGreater(p.paragraph_format.left_indent.inches, 0)

        self.assertTrue(list_found)


class TablesModuleTests(SimpleTestCase):
    def test_tables_cell_line_spacing_and_header_formatting(self):
        blocks = create_sample_structure_blocks()
        doc = rebuild_from_structure(blocks)

        t_cfg = TablesConfig(
            style="Table Grid",
            header_bold=True,
            header_fill="D9E1F2",
            cell_line_spacing=1.0,
        )
        apply_tables(doc, tables_config=t_cfg)

        self.assertEqual(len(doc.tables), 1)
        table = doc.tables[0]

        # Verificar interlineado de celda 1.0 en todas las filas
        for row in table.rows:
            for cell in row.cells:
                for p in cell.paragraphs:
                    self.assertEqual(p.paragraph_format.line_spacing, 1.0)

        # Verificar fila de encabezado
        header_row = table.rows[0]
        for cell in header_row.cells:
            for p in cell.paragraphs:
                for r in p.runs:
                    self.assertTrue(r.bold)
            self.assertTrue("D9E1F2" in cell._tc.xml)


class PageNumbersModuleTests(SimpleTestCase):
    def test_page_numbers_inserted_in_header(self):
        blocks = create_sample_structure_blocks()
        doc = rebuild_from_structure(blocks)

        apply_page_numbers(doc, enabled=True)

        for section in doc.sections:
            header_xml = section.header._element.xml
            self.assertIn("PAGE", header_xml)
            self.assertIn("fldSimple", header_xml)


class PresetsV2RebuilderIntegrationTests(SimpleTestCase):
    def test_apa7_preset_rebuilt_document(self):
        config_apa7 = load_preset("apa7")
        self.assertTrue(config_apa7.page_numbers)
        self.assertIsNotNone(config_apa7.paragraph)
        self.assertEqual(config_apa7.paragraph.first_line_indent_cm, 1.27)
        self.assertEqual(config_apa7.paragraph.alignment, "left")

        blocks = create_sample_structure_blocks()
        doc = rebuild_from_structure(blocks, config=config_apa7)

        # Verificar encabezados con keep_with_next y títulos centrados
        for p in doc.paragraphs:
            name = p.style.name if p.style else ""
            if "Heading 1" in name:
                self.assertTrue(p.paragraph_format.keep_with_next)
                self.assertEqual(p.alignment, WD_ALIGN_PARAGRAPH.CENTER)
                self.assertTrue(p.runs[0].bold)
            elif name == "Normal":
                expected_indent = Inches(1.27 / 2.54)
                self.assertAlmostEqual(p.paragraph_format.first_line_indent.inches, expected_indent.inches, places=2)

        # Verificar interlineado en celdas de tabla (1.0)
        table = doc.tables[0]
        for row in table.rows:
            for cell in row.cells:
                for p in cell.paragraphs:
                    self.assertEqual(p.paragraph_format.line_spacing, 1.0)

        # Verificar número de página
        header_xml = doc.sections[0].header._element.xml
        self.assertIn("PAGE", header_xml)

    def test_reporte_preset_rebuilt_document(self):
        config_reporte = load_preset("reporte")
        self.assertEqual(config_reporte.paragraph.alignment, "justify")
        self.assertTrue(config_reporte.tables.header_bold)
        self.assertIsNotNone(config_reporte.tables.header_fill)

        blocks = create_sample_structure_blocks()
        doc = rebuild_from_structure(blocks, config=config_reporte)

        # Verificar justificado
        for p in doc.paragraphs:
            if p.style and p.style.name == "Normal":
                self.assertEqual(p.alignment, WD_ALIGN_PARAGRAPH.JUSTIFY)

        # Verificar tabla sombreada
        header_cell_xml = doc.tables[0].rows[0].cells[0]._tc.xml
        self.assertIn("D9E1F2", header_cell_xml)

    def test_tesis_preset_rebuilt_document(self):
        config_tesis = load_preset("tesis")
        self.assertEqual(config_tesis.font_name, "Arial")
        self.assertEqual(config_tesis.margin_left, 3.0)
        self.assertEqual(config_tesis.paragraph.alignment, "justify")
        self.assertEqual(config_tesis.paragraph.first_line_indent_cm, 1.0)

        blocks = create_sample_structure_blocks()
        doc = rebuild_from_structure(blocks, config=config_tesis)

        self.assertEqual(round(doc.sections[0].left_margin.cm, 1), 3.0)


class TemplateConfigAITests(SimpleTestCase):
    def test_template_config_accepts_use_ai_true_with_submodel(self):
        cfg = TemplateConfig(
            margin_top=2.5,
            margin_bottom=2.5,
            margin_left=2.5,
            margin_right=2.5,
            font_name="Calibri",
            font_size=11,
            line_spacing=1.15,
            use_ai=True,
            ai={
                "document_type": "academico",
                "detect_titles": True,
                "detect_lists": True,
                "detect_tables": True,
                "emphasis": "medio",
                "accepted_disclaimer": True,
            }
        )
        self.assertTrue(cfg.use_ai)
        self.assertIsNotNone(cfg.ai)
        self.assertEqual(cfg.ai.document_type, "academico")
        self.assertEqual(cfg.ai.emphasis, "medio")
        self.assertTrue(cfg.ai.detect_titles)

    def test_template_config_accepts_flat_ai_fields(self):
        cfg = TemplateConfig(
            margin_top=2.5,
            margin_bottom=2.5,
            margin_left=2.5,
            margin_right=2.5,
            font_name="Calibri",
            font_size=11,
            line_spacing=1.15,
            use_ai=True,
            document_type="reporte",
            emphasis="ligero",
        )
        self.assertTrue(cfg.use_ai)
        self.assertIsNotNone(cfg.ai)
        self.assertEqual(cfg.ai.document_type, "reporte")
        self.assertEqual(cfg.ai.emphasis, "ligero")

