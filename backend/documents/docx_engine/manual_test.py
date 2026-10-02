import os
from extractor import extract_structure
from rebuilder import rebuild_from_structure
from comparator import compare_documents, compare_tables

base = os.path.dirname(os.path.abspath(__file__))

test_files = [
    "1_parrafos.docx",
    "2_tabla.docx",
    "3_celda_combinada.docx",
    "4_imagen.docx",
    "5_lista.docx"
]

for filename in test_files:
    print(f"\n{'='*50}\nPrueba para: {filename}\n{'='*50}")
    ORIGINAL = os.path.join(base, filename)
    RESULTADO = os.path.join(base, f"resultado_{filename}")
    
    if not os.path.exists(ORIGINAL):
        print(f"Archivo no encontrado: {filename}")
        continue
        
    try:
        # 1. Extraer
        with open(ORIGINAL, "rb") as f:
            blocks = extract_structure(f)
        
        # 2. Reconstruir
        doc = rebuild_from_structure(blocks)
        doc.save(RESULTADO)
        
        # 3. Comparar original vs reconstruido
        report = compare_documents(ORIGINAL, RESULTADO)
        table_diffs = compare_tables(ORIGINAL, RESULTADO)
        
        print("=== Reporte de texto/estilos ===")
        import json
        print(json.dumps(report, indent=2, ensure_ascii=False))
        
        print("\n=== Reporte de tablas ===")
        print(table_diffs if table_diffs else "Sin diferencias en tablas")
        
    except Exception as e:
        print(f"Error procesando {filename}: {e}")

