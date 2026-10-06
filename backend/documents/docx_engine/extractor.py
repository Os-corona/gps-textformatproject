import os
import tempfile
import itertools

import docx
from docx.document import Document
from docx.oxml.ns import qn
from docx.oxml.text.paragraph import CT_P
from docx.oxml.table import CT_Tbl
from docx.table import Table, _Cell
from docx.text.paragraph import Paragraph

IMG_DIR = os.path.join(tempfile.gettempdir(), "doc_images")
os.makedirs(IMG_DIR, exist_ok=True)
_img_counter = itertools.count(1)


# ---------- Imágenes ----------
def detect_inline_images(paragraph, doc_part):
    """Lista de rutas de imágenes del párrafo, o False si no hay."""
    paths = []
    for blip in paragraph._p.iter(qn("a:blip")):
        rid = blip.get(qn("r:embed"))
        if not rid or rid not in doc_part.related_parts:
            continue
        image_part = doc_part.related_parts[rid]
        ext = os.path.splitext(str(image_part.partname))[1] or ".png"
        path = os.path.join(IMG_DIR, f"img_{next(_img_counter)}{ext}")
        with open(path, "wb") as f:
            f.write(image_part.blob)
        paths.append(path)
    return paths or False


# ---------- Listas ----------
def _numbering_format(doc_part, num_id, level):
    try:
        numbering = doc_part.numbering_part.element
    except NotImplementedError:
        return None

    abstract_id = None
    for num in numbering.findall(qn("w:num")):
        if num.get(qn("w:numId")) == str(num_id):
            abstract_id = num.find(qn("w:abstractNumId")).get(qn("w:val"))
            break
    if abstract_id is None:
        return None

    for abstract in numbering.findall(qn("w:abstractNum")):
        if abstract.get(qn("w:abstractNumId")) == abstract_id:
            for lvl in abstract.findall(qn("w:lvl")):
                if lvl.get(qn("w:ilvl")) == str(level):
                    fmt = lvl.find(qn("w:numFmt"))
                    return fmt.get(qn("w:val")) if fmt is not None else None
    return None


def detect_list_info(paragraph, doc_part):
    info = {"is_list": False, "is_numbered": False, "level": 0}

    pPr = paragraph._p.pPr
    numPr = pPr.numPr if pPr is not None else None
    if numPr is not None and numPr.numId is not None and numPr.numId.val != 0:
        level = numPr.ilvl.val if numPr.ilvl is not None else 0
        fmt = _numbering_format(doc_part, numPr.numId.val, level)
        info.update(is_list=True, level=level,
                    is_numbered=(fmt not in (None, "bullet")))
        return info

    style_name = paragraph.style.name if paragraph.style is not None else ""
    if style_name.startswith("List Bullet"):
        info["is_list"] = True
    elif style_name.startswith("List Number"):
        info.update(is_list=True, is_numbered=True)
    return info


# ---------- Tablas ----------
def cell_merge_info(cell):
    tcPr = cell._tc.tcPr
    h_span = 1
    v_merge = None  # None, "restart" o "continue"
    if tcPr is not None:
        gs = tcPr.find(qn("w:gridSpan"))
        if gs is not None:
            h_span = int(gs.get(qn("w:val")))
        vm = tcPr.find(qn("w:vMerge"))
        if vm is not None:
            v_merge = vm.get(qn("w:val")) or "continue"
    return h_span, v_merge


def extract_table(table):
    rows = []
    for row in table.rows:
        row_cells = []
        for tc in row._tr.tc_lst:          # una entrada por celda real
            cell = _Cell(tc, table)
            h_span, v_merge = cell_merge_info(cell)
            row_cells.append({
                "text": cell.text.strip(),
                "h_span": h_span,
                "v_merge": v_merge,
            })
        rows.append(row_cells)
    return rows


# ---------- Estructura principal ----------
def extract_structure(file_obj):
    document = docx.Document(file_obj)
    doc_part = document.part
    blocks = []

    for block in iter_block_items(document):

        if isinstance(block, Paragraph):
            images = detect_inline_images(block, doc_part)

            # Solo se omite si no hay texto NI imagen
            if not block.text.strip() and not images:
                continue

            runs_data = []
            for run in block.runs:
                if run.text:
                    runs_data.append({
                        "text": run.text,
                        "bold": run.bold,
                        "italic": run.italic,
                        "font": run.font.name,
                        "size": run.font.size.pt if run.font.size else None
                    })

            blocks.append({
                "type": "paragraph",
                "style_name": block.style.name,
                "text": block.text,
                "runs": runs_data,
                "has_inline_image": images,
                "list_info": detect_list_info(block, doc_part),
            })

        elif isinstance(block, Table):
            rows = extract_table(block)
            blocks.append({
                "type": "table",
                "rows": rows,
                # compatibilidad con código anterior (solo textos)
                "data": [[c["text"] for c in row] for row in rows],
            })

    return blocks


def iter_block_items(parent):
    if isinstance(parent, Document):
        parent_elm = parent.element.body
    else:
        parent_elm = parent._element

    for child in parent_elm.iterchildren():
        if isinstance(child, CT_P):
            yield Paragraph(child, parent)
        elif isinstance(child, CT_Tbl):
            yield Table(child, parent)