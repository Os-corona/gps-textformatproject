import os
from extractor import extract_structure
from rebuilder import rebuild_from_structure

base = os.path.dirname(os.path.abspath(__file__))
nombres = ["docPruebas.docx"]   # agrega aquí los demás cuando los crees

for nombre in nombres:
    ruta = os.path.join(base, nombre)
    if not os.path.exists(ruta):
        print("No existe:", ruta)
        continue

    with open(ruta, "rb") as f:
        bloques = extract_structure(f)

    for b in bloques:
        if b["type"] == "paragraph":
            print("P", b["list_info"], b["has_inline_image"], b["text"][:40])
        else:
            print("T", len(b["rows"]), "filas")

    doc = rebuild_from_structure(bloques)
    salida = os.path.join(base, "reconstruido_" + nombre)
    doc.save(salida)
    print("Guardado:", salida)