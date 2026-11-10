from pathlib import Path
from docx import Document
from docx.oxml.ns import qn


def _ensure_doc(doc_or_path):
    """Retorna una instancia de Document a partir de una ruta o de un Document existente."""
    if hasattr(doc_or_path, "paragraphs") and hasattr(doc_or_path, "tables"):
        return doc_or_path
    return Document(str(doc_or_path))


def compare_documents(path_a, path_b):
    """
    Compara los párrafos con texto no vacío y sus estilos entre dos documentos.
    Retorna un diccionario con listas de diferencias detectadas.
    """
    doc_a = _ensure_doc(path_a)
    doc_b = _ensure_doc(path_b)

    report = {
        "text_diff": [],
        "style_diff": [],
        "structure_diff": [],
    }

    paras_a = [p for p in doc_a.paragraphs if p.text.strip()]
    paras_b = [p for p in doc_b.paragraphs if p.text.strip()]

    if len(paras_a) != len(paras_b):
        report["structure_diff"].append(
            f"Número de párrafos distinto: {len(paras_a)} vs {len(paras_b)}"
        )

    for i, (pa, pb) in enumerate(zip(paras_a, paras_b)):
        if pa.text != pb.text:
            report["text_diff"].append({
                "index": i, "original": pa.text, "rebuilt": pb.text
            })
        if pa.style.name != pb.style.name:
            report["style_diff"].append({
                "index": i, "original": pa.style.name, "rebuilt": pb.style.name
            })

    return report


def compare_tables(path_a, path_b):
    """
    Compara el número de tablas y el texto de cada una de sus celdas.
    Retorna una lista de diferencias (vacía si son idénticas).
    """
    doc_a = _ensure_doc(path_a)
    doc_b = _ensure_doc(path_b)
    diffs = []

    if len(doc_a.tables) != len(doc_b.tables):
        diffs.append(f"Número de tablas distinto: {len(doc_a.tables)} vs {len(doc_b.tables)}")
        return diffs

    for t, (table_a, table_b) in enumerate(zip(doc_a.tables, doc_b.tables)):
        for i, (row_a, row_b) in enumerate(zip(table_a.rows, table_b.rows)):
            for j, (cell_a, cell_b) in enumerate(zip(row_a.cells, row_b.cells)):
                if cell_a.text != cell_b.text:
                    diffs.append(f"Tabla {t}, celda ({i},{j}): '{cell_a.text}' vs '{cell_b.text}'")

    return diffs


def _cell_merge_info(cell):
    """Extrae la información de combinación (gridSpan y vMerge) de una celda XML."""
    tcPr = cell._tc.tcPr
    h_span = 1
    v_merge = None
    if tcPr is not None:
        gs = tcPr.find(qn("w:gridSpan"))
        if gs is not None:
            h_span = int(gs.get(qn("w:val")))
        vm = tcPr.find(qn("w:vMerge"))
        if vm is not None:
            v_merge = vm.get(qn("w:val")) or "continue"
    return h_span, v_merge


def compare_merged_cells(path_a, path_b):
    """
    Compara la estructura de celdas combinadas (spans horizontales y verticales)
    en todas las tablas de ambos documentos.
    Retorna una lista de diferencias (vacía si son idénticas).
    """
    doc_a = _ensure_doc(path_a)
    doc_b = _ensure_doc(path_b)
    diffs = []

    if len(doc_a.tables) != len(doc_b.tables):
        diffs.append(f"Número de tablas distinto: {len(doc_a.tables)} vs {len(doc_b.tables)}")
        return diffs

    for t, (table_a, table_b) in enumerate(zip(doc_a.tables, doc_b.tables)):
        if len(table_a.rows) != len(table_b.rows):
            diffs.append(f"Tabla {t}: número de filas distinto ({len(table_a.rows)} vs {len(table_b.rows)})")
            continue
        for i, (row_a, row_b) in enumerate(zip(table_a.rows, table_b.rows)):
            if len(row_a.cells) != len(row_b.cells):
                diffs.append(f"Tabla {t}, fila {i}: número de celdas distinto ({len(row_a.cells)} vs {len(row_b.cells)})")
                continue
            for j, (cell_a, cell_b) in enumerate(zip(row_a.cells, row_b.cells)):
                span_a, vm_a = _cell_merge_info(cell_a)
                span_b, vm_b = _cell_merge_info(cell_b)
                if span_a != span_b or vm_a != vm_b:
                    diffs.append(
                        f"Tabla {t}, celda ({i},{j}) combinación distinta: "
                        f"(h_span={span_a}, v_merge={vm_a}) vs (h_span={span_b}, v_merge={vm_b})"
                    )
    return diffs


def compare_images(path_a, path_b):
    """
    Compara el número de imágenes embebidas (a:blip) entre ambos documentos.
    Retorna una lista de diferencias (vacía si son idénticas).
    """
    doc_a = _ensure_doc(path_a)
    doc_b = _ensure_doc(path_b)
    diffs = []

    count_a = len(doc_a.element.xpath(".//a:blip"))
    count_b = len(doc_b.element.xpath(".//a:blip"))
    if count_a != count_b:
        diffs.append(f"Número de imágenes distinto: {count_a} vs {count_b}")

    return diffs


def compare_sections(path_a, path_b):
    """
    Compara el número de secciones y sus orientaciones entre ambos documentos.
    Retorna una lista de diferencias (vacía si son idénticas).
    """
    doc_a = _ensure_doc(path_a)
    doc_b = _ensure_doc(path_b)
    diffs = []

    if len(doc_a.sections) != len(doc_b.sections):
        diffs.append(f"Número de secciones distinto: {len(doc_a.sections)} vs {len(doc_b.sections)}")
        return diffs

    for i, (sec_a, sec_b) in enumerate(zip(doc_a.sections, doc_b.sections)):
        if sec_a.orientation != sec_b.orientation:
            diffs.append(
                f"Sección {i}: orientación distinta: {sec_a.orientation} vs {sec_b.orientation}"
            )

    return diffs
