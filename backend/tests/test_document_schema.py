"""
Pruebas unitarias de serialización ida y vuelta y validaciones
del Esquema de Documento Intermedio (S3T9).
"""

import json
from pathlib import Path
from django.test import SimpleTestCase
from pydantic import ValidationError

from common.document_schema import (
    SCHEMA_VERSION,
    Run,
    Hints,
    TableCell,
    SourceBlock,
    ParagraphOutBlock,
    HeadingOutBlock,
    ListItemOutBlock,
    TableOutBlock,
    ImageOutBlock,
    AIChunkInput,
    AIChunkOutput,
    IntegrityReport,
    export_json_schemas,
)


class RunSerializationAndValidationTests(SimpleTestCase):
    def test_run_roundtrip_serialization(self):
        run = Run(
            text="Texto de prueba",
            bold=True,
            italic=False,
            underline=True,
            font="Arial",
            size=12.5,
            color="#333333",
        )
        # Ida y vuelta via dict
        run_dict = run.model_dump()
        restored_from_dict = Run.model_validate(run_dict)
        self.assertEqual(restored_from_dict, run)

        # Ida y vuelta via JSON
        run_json = run.model_dump_json()
        restored_from_json = Run.model_validate_json(run_json)
        self.assertEqual(restored_from_json, run)

    def test_run_empty_text_raises_validation_error(self):
        with self.assertRaises(ValidationError):
            Run(text="")

    def test_run_default_optional_fields(self):
        run = Run(text="Simple")
        self.assertIsNone(run.bold)
        self.assertIsNone(run.font)
        self.assertEqual(run.text, "Simple")


class HintsSerializationAndValidationTests(SimpleTestCase):
    def test_hints_roundtrip_serialization(self):
        hints = Hints(
            style_name="Heading 1",
            suggested_type="heading",
            suggested_level=1,
            is_list=False,
            is_numbered=False,
            list_level=0,
            has_inline_image=False,
            keep_with_next=True,
            grammar_checked=True,
            confidence=0.98,
            notes="Encabezado principal detectado",
            custom_extra_attribute="valor_extra",
        )
        hints_json = hints.model_dump_json()
        restored = Hints.model_validate_json(hints_json)
        self.assertEqual(restored.style_name, "Heading 1")
        self.assertEqual(restored.suggested_level, 1)
        self.assertEqual(getattr(restored, "custom_extra_attribute"), "valor_extra")

    def test_hints_level_out_of_range(self):
        with self.assertRaises(ValidationError):
            Hints(suggested_level=10)

        with self.assertRaises(ValidationError):
            Hints(suggested_level=-1)

        with self.assertRaises(ValidationError):
            Hints(list_level=9)


class SourceBlockSerializationAndValidationTests(SimpleTestCase):
    def test_source_paragraph_roundtrip(self):
        block = SourceBlock(
            id="src-001",
            type="paragraph",
            text="Párrafo original completo",
            runs=[Run(text="Párrafo original "), Run(text="completo", bold=True)],
            hints=Hints(style_name="Normal"),
        )
        block_json = block.model_dump_json()
        restored = SourceBlock.model_validate_json(block_json)
        self.assertEqual(restored.id, "src-001")
        self.assertEqual(restored.type, "paragraph")
        self.assertEqual(len(restored.runs), 2)
        self.assertEqual(restored.runs[1].bold, True)

    def test_source_table_rectangular_validation(self):
        # Tabla rectangular: fila 0 ancho 2, fila 1 ancho 2 (1 celda con h_span=2)
        valid_table = SourceBlock(
            id="tbl-001",
            type="table",
            rows=[
                [TableCell(text="A1", h_span=1), TableCell(text="B1", h_span=1)],
                [TableCell(text="A2_span2", h_span=2)],
            ]
        )
        dumped = valid_table.model_dump_json()
        restored = SourceBlock.model_validate_json(dumped)
        self.assertEqual(len(restored.rows), 2)

        # Tabla NO rectangular
        with self.assertRaises(ValidationError):
            SourceBlock(
                id="tbl-bad",
                type="table",
                rows=[
                    [TableCell(text="A1", h_span=1), TableCell(text="B1", h_span=1)],
                    [TableCell(text="A2", h_span=1)],  # Ancho 1 != Ancho 2
                ]
            )

    def test_source_runs_empty_list_fails(self):
        with self.assertRaises(ValidationError):
            SourceBlock(type="paragraph", runs=[])


class OutBlockDiscriminatedUnionTests(SimpleTestCase):
    def test_paragraph_outblock_roundtrip(self):
        block = ParagraphOutBlock(
            id="p-1",
            runs=[Run(text="Texto de párrafo"), Run(text=" en negrita", bold=True)]
        )
        self.assertEqual(block.type, "paragraph")
        restored = ParagraphOutBlock.model_validate_json(block.model_dump_json())
        self.assertEqual(restored, block)

    def test_paragraph_outblock_empty_runs_fails(self):
        with self.assertRaises(ValidationError):
            ParagraphOutBlock(runs=[])

    def test_heading_outblock_levels(self):
        for lvl in range(1, 7):
            h = HeadingOutBlock(level=lvl, runs=[Run(text=f"Título H{lvl}")])
            self.assertEqual(h.level, lvl)

        # Nivel menor a 1
        with self.assertRaises(ValidationError):
            HeadingOutBlock(level=0, runs=[Run(text="Inválido")])

        # Nivel mayor a 6
        with self.assertRaises(ValidationError):
            HeadingOutBlock(level=7, runs=[Run(text="Inválido")])

    def test_list_item_outblock_levels_and_type(self):
        for lvl in range(0, 9):
            item = ListItemOutBlock(level=lvl, is_numbered=True, runs=[Run(text=f"Item {lvl}")])
            self.assertEqual(item.level, lvl)
            self.assertTrue(item.is_numbered)

        # Nivel de lista mayor a 8
        with self.assertRaises(ValidationError):
            ListItemOutBlock(level=9, runs=[Run(text="Inválido")])

    def test_table_outblock_rectangular_with_hspan(self):
        # 3 columnas en total:
        # Fila 0: 3 celdas (1 + 1 + 1 = 3)
        # Fila 1: 1 celda span 2, 1 celda span 1 (2 + 1 = 3)
        # Fila 2: 1 celda span 3 (3)
        table = TableOutBlock(
            rows=[
                [TableCell(text="C1", h_span=1), TableCell(text="C2", h_span=1), TableCell(text="C3", h_span=1)],
                [TableCell(text="Span2", h_span=2), TableCell(text="C4", h_span=1)],
                [TableCell(text="Span3", h_span=3)],
            ]
        )
        restored = TableOutBlock.model_validate_json(table.model_dump_json())
        self.assertEqual(len(restored.rows), 3)

        # Tabla con fila descuadrada (3 columnas vs 2 columnas)
        with self.assertRaises(ValidationError):
            TableOutBlock(
                rows=[
                    [TableCell(text="A", h_span=1), TableCell(text="B", h_span=1), TableCell(text="C", h_span=1)],
                    [TableCell(text="D", h_span=1), TableCell(text="E", h_span=1)],
                ]
            )

    def test_image_outblock_roundtrip(self):
        img = ImageOutBlock(image_path="/tmp/img1.png", caption="Figura 1")
        restored = ImageOutBlock.model_validate_json(img.model_dump_json())
        self.assertEqual(restored.type, "image")
        self.assertEqual(restored.image_path, "/tmp/img1.png")


class AIChunkInputOutputRoundtripTests(SimpleTestCase):
    def test_aichunk_input_roundtrip(self):
        chunk_input = AIChunkInput(
            schema_version=SCHEMA_VERSION,
            chunk_id="chunk-input-001",
            document_id=42,
            blocks=[
                SourceBlock(id="b1", type="paragraph", runs=[Run(text="Hola")]),
                SourceBlock(id="b2", type="heading", level=2, runs=[Run(text="Subtítulo")]),
            ],
            hints=Hints(style_name="Normal"),
        )
        json_data = chunk_input.model_dump_json()
        restored = AIChunkInput.model_validate_json(json_data)
        self.assertEqual(restored.schema_version, "di.v1")
        self.assertEqual(restored.chunk_id, "chunk-input-001")
        self.assertEqual(restored.document_id, 42)
        self.assertEqual(len(restored.blocks), 2)
        self.assertEqual(restored.blocks[1].level, 2)

    def test_aichunk_input_invalid_version_raises(self):
        with self.assertRaises(ValidationError):
            AIChunkInput(schema_version="di.v2_invalida", chunk_id="chk-1")

    def test_aichunk_output_polymorphic_blocks_roundtrip(self):
        chunk_output = AIChunkOutput(
            schema_version=SCHEMA_VERSION,
            chunk_id="chunk-out-001",
            summary="Se convirtieron párrafos a títulos y elementos de lista.",
            blocks=[
                ParagraphOutBlock(id="o1", runs=[Run(text="Introducción")]),
                HeadingOutBlock(id="o2", level=1, runs=[Run(text="Capítulo 1")]),
                ListItemOutBlock(id="o3", level=0, is_numbered=False, runs=[Run(text="Punto A")]),
                TableOutBlock(
                    id="o4",
                    rows=[
                        [TableCell(text="K1"), TableCell(text="V1")],
                        [TableCell(text="K2"), TableCell(text="V2")],
                    ]
                ),
                ImageOutBlock(id="o5", image_path="images/logo.png", caption="Logo"),
            ],
        )

        json_str = chunk_output.model_dump_json()
        restored = AIChunkOutput.model_validate_json(json_str)

        self.assertEqual(restored.schema_version, "di.v1")
        self.assertEqual(restored.chunk_id, "chunk-out-001")
        self.assertEqual(len(restored.blocks), 5)

        # Verificar que la unión discriminada instanció las subclases correctas
        self.assertIsInstance(restored.blocks[0], ParagraphOutBlock)
        self.assertIsInstance(restored.blocks[1], HeadingOutBlock)
        self.assertIsInstance(restored.blocks[2], ListItemOutBlock)
        self.assertIsInstance(restored.blocks[3], TableOutBlock)
        self.assertIsInstance(restored.blocks[4], ImageOutBlock)

        self.assertEqual(restored.blocks[1].level, 1)
        self.assertEqual(restored.blocks[2].is_numbered, False)

    def test_aichunk_output_invalid_block_type_raises(self):
        invalid_data = {
            "schema_version": "di.v1",
            "chunk_id": "c-1",
            "blocks": [
                {"type": "tipo_inexistente", "runs": [{"text": "abc"}]}
            ]
        }
        with self.assertRaises(ValidationError):
            AIChunkOutput.model_validate(invalid_data)


class IntegrityReportTests(SimpleTestCase):
    def test_integrity_report_roundtrip(self):
        report = IntegrityReport(
            schema_version=SCHEMA_VERSION,
            is_valid=True,
            total_source_blocks=10,
            total_out_blocks=10,
            source_characters=1520,
            out_characters=1518,
            warnings=["Diferencia de 2 caracteres en signos de puntuación corregidos."],
            errors=[],
            preserved_elements={"tables": True, "images": True, "lists": True},
            similarity_score=0.998,
            metadata={"checked_by": "integrity_checker_v1"},
        )

        dumped = report.model_dump_json()
        restored = IntegrityReport.model_validate_json(dumped)

        self.assertEqual(restored.schema_version, "di.v1")
        self.assertTrue(restored.is_valid)
        self.assertEqual(restored.total_source_blocks, 10)
        self.assertEqual(restored.similarity_score, 0.998)
        self.assertEqual(len(restored.warnings), 1)
        self.assertEqual(len(restored.errors), 0)

    def test_integrity_report_invalid_schema_version_raises(self):
        with self.assertRaises(ValidationError):
            IntegrityReport(schema_version="invalida", is_valid=True)


class ExportJsonSchemasTests(SimpleTestCase):
    def test_export_json_schemas_creates_valid_files(self):
        exported = export_json_schemas()
        self.assertIn("aichunk_output.schema.json", exported)
        self.assertIn("aichunk_input.schema.json", exported)
        self.assertIn("integrity_report.schema.json", exported)
        self.assertIn("source_block.schema.json", exported)

        for filename, filepath_str in exported.items():
            path = Path(filepath_str)
            self.assertTrue(path.exists(), f"El archivo {filename} no fue generado.")
            content = path.read_text(encoding="utf-8")
            data = json.loads(content)
            self.assertIn("$schema", data)
            self.assertEqual(data.get("schema_version"), "di.v1")

