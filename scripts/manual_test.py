"""
Script de prueba manual para docx_engine (S3T8).

Ejecuta el roundtrip de extracción y reconstrucción sobre los fixtures
en tests/fixtures/ y reporta las diferencias usando comparator.
"""

import os
import sys
import json
import tempfile
from pathlib import Path

# Agregar directorio backend a sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = BASE_DIR / "backend"
FIXTURES_DIR = BACKEND_DIR / "tests" / "fixtures"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from docx_engine.extractor import extract_structure
from docx_engine.rebuilder import rebuild_from_structure
from docx_engine.comparator import (
    compare_documents,
    compare_tables,
    compare_images,
    compare_merged_cells,
    compare_sections,
)

FIXTURE_NAMES = [
    "01_planos.docx",
    "02_headings_mixto.docx",
    "03_tema.docx",
    "04_tabla_imagen.docx",
    "05_listas.docx",
    "06_secciones.docx",
]

OUTPUT_DIR = Path(tempfile.gettempdir()) / "docx_engine_manual_test"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def run_manual_test():
    print(f"Directorio de fixtures: {FIXTURES_DIR}")
    print(f"Directorio de salida:   {OUTPUT_DIR}\n")

    for filename in FIXTURE_NAMES:
        print("=" * 60)
        print(f"Prueba manual para: {filename}")
        print("=" * 60)

        original_path = FIXTURES_DIR / filename
        rebuilt_path = OUTPUT_DIR / f"rebuilt_{filename}"

        if not original_path.exists():
            print(f"[AVISO] Archivo no encontrado: {original_path}")
            continue

        try:
            # 1. Extraer
            with open(original_path, "rb") as f:
                blocks = extract_structure(f)
            print(f"Extracción exitosa: {len(blocks)} bloques extraídos.")

            # 2. Reconstruir
            doc = rebuild_from_structure(blocks)
            doc.save(str(rebuilt_path))
            print(f"Guardado reconstruido: {rebuilt_path}")

            # 3. Comparaciones
            doc_report = compare_documents(original_path, rebuilt_path)
            table_diffs = compare_tables(original_path, rebuilt_path)
            image_diffs = compare_images(original_path, rebuilt_path)
            merged_diffs = compare_merged_cells(original_path, rebuilt_path)
            section_diffs = compare_sections(original_path, rebuilt_path)

            print("\n--- Textos ---")
            if doc_report["text_diff"]:
                print(f"Diferencias de texto ({len(doc_report['text_diff'])}):")
                print(json.dumps(doc_report["text_diff"], indent=2, ensure_ascii=False))
            else:
                print("Textos idénticos.")

            print("\n--- Tablas ---")
            print(table_diffs if table_diffs else "Sin diferencias en tablas.")

            print("\n--- Celdas combinadas ---")
            print(merged_diffs if merged_diffs else "Sin diferencias en celdas combinadas.")

            print("\n--- Imágenes ---")
            print(image_diffs if image_diffs else "Sin diferencias en imágenes.")

            print("\n--- Secciones ---")
            print(section_diffs if section_diffs else "Sin diferencias en secciones.")

        except Exception as e:
            print(f"[ERROR] Error procesando {filename}: {e}")

        print()


if __name__ == "__main__":
    run_manual_test()

