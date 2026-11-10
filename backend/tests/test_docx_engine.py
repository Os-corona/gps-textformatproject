"""
Pruebas de roundtrip (extracción y reconstrucción) para docx_engine (S3T8).

Valida el ciclo extract -> rebuild sobre la suite de 6 fixtures estándar:
- 01_planos.docx
- 02_headings_mixto.docx
- 03_tema.docx
- 04_tabla_imagen.docx
- 05_listas.docx
- 06_secciones.docx

Utiliza las funciones de 'comparator' para verificar la fidelidad de:
1. Párrafos y textos.
2. Número de tablas y contenido de celdas.
3. Imágenes embebidas (a:blip).
4. Celdas combinadas (spans horizontales y verticales).
5. Secciones y orientaciones (06_secciones se marca como xfail documentado hasta S3T5).
"""

from pathlib import Path
import pytest
from docx import Document
from docx.enum.section import WD_ORIENT

from docx_engine.extractor import extract_structure
from docx_engine.rebuilder import rebuild_from_structure
from docx_engine.comparator import (
    compare_documents,
    compare_tables,
    compare_images,
    compare_merged_cells,
    compare_sections,
)

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"

ALL_FIXTURE_NAMES = [
    "01_planos.docx",
    "02_headings_mixto.docx",
    "03_tema.docx",
    "04_tabla_imagen.docx",
    "05_listas.docx",
    "06_secciones.docx",
]

ROUNDTRIP_PARAMS = [
    "01_planos.docx",
    "02_headings_mixto.docx",
    "03_tema.docx",
    "04_tabla_imagen.docx",
    "05_listas.docx",
    pytest.param(
        "06_secciones.docx",
        marks=pytest.mark.xfail(
            reason=(
                "Caso conocido (deuda técnica): 06_secciones pierde secciones y "
                "orientación durante el rebuild v1; se resolverá en S3T5 con Rebuilder v2."
            ),
            strict=True,
        ),
    ),
]


@pytest.fixture(params=ALL_FIXTURE_NAMES)
def fixture_path(request):
    """Provee la ruta absoluta a cada uno de los 6 fixtures válidos."""
    path = FIXTURES_DIR / request.param
    assert path.exists(), f"Fixture no encontrado: {path}"
    return path


# ---------------------------------------------------------------------------
# Requisito 1 y 2: Roundtrip completo extract -> rebuild con comparator
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("fixture_name", ROUNDTRIP_PARAMS)
def test_docx_engine_roundtrip_full_integrity(fixture_name, tmp_path):
    """
    Roundtrip completo: extract -> rebuild -> save.
    Verifica mediante comparator:
    - Textos de párrafos idénticos sin pérdida.
    - Número de tablas y textos de celdas idénticos.
    - Conteo de imágenes preservado.
    - Celdas combinadas (gridSpan y vMerge) idénticas.
    - Número de secciones y orientación (xfail en 06_secciones hasta S3T5).
    """
    original_path = FIXTURES_DIR / fixture_name
    assert original_path.exists(), f"Fixture no existe: {original_path}"

    with open(original_path, "rb") as f:
        blocks = extract_structure(f)

    assert len(blocks) > 0, f"La extracción no produjo bloques para {fixture_name}"

    rebuilt_doc = rebuild_from_structure(blocks)
    rebuilt_path = tmp_path / f"rebuilt_{fixture_name}"
    rebuilt_doc.save(str(rebuilt_path))

    # 1. Comparar textos
    doc_report = compare_documents(original_path, rebuilt_path)
    assert not doc_report["text_diff"], (
        f"Diferencias en textos para '{fixture_name}': {doc_report['text_diff']}"
    )

    # 2. Comparar tablas
    table_diffs = compare_tables(original_path, rebuilt_path)
    assert not table_diffs, (
        f"Diferencias en tablas para '{fixture_name}': {table_diffs}"
    )

    # 3. Comparar imágenes
    image_diffs = compare_images(original_path, rebuilt_path)
    assert not image_diffs, (
        f"Diferencias en imágenes para '{fixture_name}': {image_diffs}"
    )

    # 4. Comparar celdas combinadas
    merged_diffs = compare_merged_cells(original_path, rebuilt_path)
    assert not merged_diffs, (
        f"Diferencias en celdas combinadas para '{fixture_name}': {merged_diffs}"
    )

    # 5. Comparar secciones (06_secciones falla aquí y dispara el xfail documentado)
    section_diffs = compare_sections(original_path, rebuilt_path)
    assert not section_diffs, (
        f"Diferencias en secciones para '{fixture_name}': {section_diffs}"
    )


# ---------------------------------------------------------------------------
# Pruebas específicas y aisladas de componentes
# ---------------------------------------------------------------------------

def test_roundtrip_text_preservation_all_fixtures(fixture_path, tmp_path):
    """
    Verifica que el texto plano de todos los párrafos se conserve exactamente
    en los 6 fixtures, incluyendo 06_secciones (el texto no se pierde, solo las secciones).
    """
    with open(fixture_path, "rb") as f:
        blocks = extract_structure(f)

    rebuilt_doc = rebuild_from_structure(blocks)
    rebuilt_path = tmp_path / f"rebuilt_text_{fixture_path.name}"
    rebuilt_doc.save(str(rebuilt_path))

    doc_report = compare_documents(fixture_path, rebuilt_path)
    assert not doc_report["text_diff"], (
        f"Discrepancia en textos para '{fixture_path.name}': {doc_report['text_diff']}"
    )


def test_roundtrip_tables_and_merged_cells_preservation(tmp_path):
    """
    Prueba enfocada en tablas y celdas combinadas sobre 04_tabla_imagen.docx.
    Valida número de tablas, dimensiones y combinación horizontal/vertical.
    """
    original_path = FIXTURES_DIR / "04_tabla_imagen.docx"
    with open(original_path, "rb") as f:
        blocks = extract_structure(f)

    table_blocks = [b for b in blocks if b["type"] == "table"]
    assert len(table_blocks) == 1, "04_tabla_imagen.docx debe contener exactamente 1 tabla"

    rebuilt_doc = rebuild_from_structure(blocks)
    rebuilt_path = tmp_path / "rebuilt_04_tabla.docx"
    rebuilt_doc.save(str(rebuilt_path))

    table_diffs = compare_tables(original_path, rebuilt_path)
    assert not table_diffs, f"Diferencias en celdas de tabla: {table_diffs}"

    merged_diffs = compare_merged_cells(original_path, rebuilt_path)
    assert not merged_diffs, f"Diferencias en celdas combinadas: {merged_diffs}"


def test_roundtrip_inline_images_preservation(tmp_path):
    """
    Prueba enfocada en imágenes inline sobre 04_tabla_imagen.docx.
    Verifica que la imagen se extraiga, se asocie y se reconstruya en el documento.
    """
    original_path = FIXTURES_DIR / "04_tabla_imagen.docx"
    with open(original_path, "rb") as f:
        blocks = extract_structure(f)

    image_blocks = [
        b for b in blocks
        if b["type"] == "paragraph" and b.get("has_inline_image")
    ]
    assert len(image_blocks) >= 1, "Debe detectarse al menos un párrafo con imagen inline"

    rebuilt_doc = rebuild_from_structure(blocks)
    rebuilt_path = tmp_path / "rebuilt_04_imagen.docx"
    rebuilt_doc.save(str(rebuilt_path))

    image_diffs = compare_images(original_path, rebuilt_path)
    assert not image_diffs, f"Diferencias en imágenes: {image_diffs}"


@pytest.mark.xfail(
    reason="Caso conocido: 06_secciones pierde secciones en docx_engine v1 (hasta S3T5)",
    strict=True,
)
def test_known_debt_06_secciones_loses_sections(tmp_path):
    """
    Verifica explícitamente el caso conocido de deuda técnica del Sprint 2:
    06_secciones.docx tiene 3 secciones en el original pero el rebuilder v1
    actualmente solo genera 1 sección.
    """
    original_path = FIXTURES_DIR / "06_secciones.docx"
    with open(original_path, "rb") as f:
        blocks = extract_structure(f)

    rebuilt_doc = rebuild_from_structure(blocks)
    rebuilt_path = tmp_path / "rebuilt_06_secciones.docx"
    rebuilt_doc.save(str(rebuilt_path))

    diffs = compare_sections(original_path, rebuilt_path)
    assert not diffs, f"06_secciones pierde secciones: {diffs}"


# ---------------------------------------------------------------------------
# Pruebas unitarias de las funciones de comparator
# ---------------------------------------------------------------------------

def test_comparator_detects_text_differences(tmp_path):
    """Valida que compare_documents reporte diferencias de texto con precisión."""
    doc_a = Document()
    doc_a.add_paragraph("Texto original")
    path_a = tmp_path / "doc_a.docx"
    doc_a.save(str(path_a))

    doc_b = Document()
    doc_b.add_paragraph("Texto modificado")
    path_b = tmp_path / "doc_b.docx"
    doc_b.save(str(path_b))

    report = compare_documents(path_a, path_b)
    assert len(report["text_diff"]) == 1
    assert report["text_diff"][0]["original"] == "Texto original"
    assert report["text_diff"][0]["rebuilt"] == "Texto modificado"


def test_comparator_detects_table_differences(tmp_path):
    """Valida que compare_tables reporte discrepancias en celdas de tablas."""
    doc_a = Document()
    t_a = doc_a.add_table(rows=1, cols=1)
    t_a.cell(0, 0).text = "A"
    path_a = tmp_path / "t_a.docx"
    doc_a.save(str(path_a))

    doc_b = Document()
    t_b = doc_b.add_table(rows=1, cols=1)
    t_b.cell(0, 0).text = "B"
    path_b = tmp_path / "t_b.docx"
    doc_b.save(str(path_b))

    diffs = compare_tables(path_a, path_b)
    assert len(diffs) == 1
    assert "'A' vs 'B'" in diffs[0]


def test_comparator_detects_image_differences(tmp_path):
    """Valida que compare_images reporte discrepancias en la cantidad de imágenes."""
    original_with_img = FIXTURES_DIR / "04_tabla_imagen.docx"
    plain_without_img = FIXTURES_DIR / "01_planos.docx"

    diffs = compare_images(original_with_img, plain_without_img)
    assert len(diffs) == 1
    assert "Número de imágenes distinto: 1 vs 0" in diffs[0]


def test_comparator_detects_merged_cell_differences(tmp_path):
    """Valida que compare_merged_cells detecte discrepancias en celdas combinadas."""
    # Doc A: tabla 2x2 sin combinar
    doc_a = Document()
    t_a = doc_a.add_table(rows=2, cols=2)
    path_a = tmp_path / "t_a.docx"
    doc_a.save(str(path_a))

    # Doc B: tabla 2x2 con celdas de primera fila combinadas
    doc_b = Document()
    t_b = doc_b.add_table(rows=2, cols=2)
    t_b.cell(0, 0).merge(t_b.cell(0, 1))
    path_b = tmp_path / "t_b.docx"
    doc_b.save(str(path_b))

    diffs = compare_merged_cells(path_a, path_b)
    assert len(diffs) > 0
    assert "combinación distinta" in diffs[0]


def test_comparator_detects_section_differences(tmp_path):
    """Valida que compare_sections detecte discrepancias en la cantidad de secciones."""
    multi_sec = FIXTURES_DIR / "06_secciones.docx"
    single_sec = FIXTURES_DIR / "01_planos.docx"

    diffs = compare_sections(multi_sec, single_sec)
    assert len(diffs) == 1
    assert "Número de secciones distinto: 3 vs 1" in diffs[0]
