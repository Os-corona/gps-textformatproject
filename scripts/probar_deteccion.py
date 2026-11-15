"""
Script de inspección de detección para docx_engine (S3T8).

Permite inspeccionar los bloques extraídos por extract_structure
(párrafos, encabezados, listas, imágenes, tablas) sobre los fixtures en tests/fixtures/.
"""

import sys
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


def probar_deteccion(archivos=None):
    if not archivos:
        archivos = [
            "01_planos.docx",
            "02_headings_mixto.docx",
            "03_tema.docx",
            "04_tabla_imagen.docx",
            "05_listas.docx",
            "06_secciones.docx",
        ]

    salida_dir = Path(tempfile.gettempdir()) / "docx_engine_deteccion"
    salida_dir.mkdir(parents=True, exist_ok=True)

    for nombre in archivos:
        ruta = FIXTURES_DIR / nombre
        if not ruta.exists():
            print("No existe:", ruta)
            continue

        print("=" * 60)
        print("Inspeccionando:", nombre)
        print("=" * 60)

        with open(ruta, "rb") as f:
            bloques = extract_structure(f)

        print(f"Total de bloques extraídos: {len(bloques)}")
        for idx, b in enumerate(bloques):
            if b["type"] == "paragraph":
                list_info = b.get("list_info", {})
                img_info = bool(b.get("has_inline_image"))
                txt_preview = b.get("text", "")[:45].replace("\n", " ")
                print(
                    f"[{idx:02d}] P (estilo={b.get('style_name')}, "
                    f"es_lista={list_info.get('is_list')}, "
                    f"img={img_info}): {txt_preview}"
                )
            elif b["type"] == "table":
                num_rows = len(b.get("rows", []))
                print(f"[{idx:02d}] T Tabla con {num_rows} filas.")

        doc = rebuild_from_structure(bloques)
        salida = salida_dir / f"reconstruido_{nombre}"
        doc.save(str(salida))
        print("Guardado reconstruido:", salida)
        print()


if __name__ == "__main__":
    archivos_input = sys.argv[1:] if len(sys.argv) > 1 else None
    probar_deteccion(archivos_input)

