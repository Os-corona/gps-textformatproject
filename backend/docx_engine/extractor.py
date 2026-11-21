import os
import tempfile
import itertools
import re
from collections import Counter
from os import PathLike

import docx
from lxml import etree
from docx.document import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml.text.paragraph import CT_P
from docx.oxml.table import CT_Tbl
from docx.table import Table, _Cell
from docx.text.paragraph import Paragraph

from common.document_schema import DI, ExtractionStats, Hints, Run, SourceBlock

IMG_DIR = os.path.join(tempfile.gettempdir(), "doc_images")
_img_counter = itertools.count(1)

GLYPH_RE = re.compile(r"^\s*(?:[•◦▪▫‣⁃·●○■□◆◇►▶➢]|[–—-](?:\s|$))")
MANUAL_NUMBERING_RE = re.compile(
    r"^\s*(?:\d+(?:\.\d+)+[.)]?|\d+[.)]|\(\d+(?:\.\d+)*\)|"
    r"[A-Za-z][.)]|\([A-Za-z]\)|[IVXLCDMivxlcdm]+[.)])\s+"
)
KEY_VALUE_RE = re.compile(r"^\s*(?!https?://)[^:\n]{2,40}:\s+\S+")

_ALIGNMENT_TO_STR = {
    WD_ALIGN_PARAGRAPH.LEFT: "left",
    WD_ALIGN_PARAGRAPH.CENTER: "center",
    WD_ALIGN_PARAGRAPH.RIGHT: "right",
    WD_ALIGN_PARAGRAPH.JUSTIFY: "justify",
    WD_ALIGN_PARAGRAPH.JUSTIFY_MED: "justify",
    WD_ALIGN_PARAGRAPH.JUSTIFY_HI: "justify",
    WD_ALIGN_PARAGRAPH.JUSTIFY_LOW: "justify",
    WD_ALIGN_PARAGRAPH.DISTRIBUTE: "justify",
}


def _is_all_caps(text: str) -> bool:
    letters = [ch for ch in text if ch.isalpha()]
    return len(letters) >= 2 and all(ch.isupper() for ch in letters)


def _paragraph_alignment(paragraph) -> str | None:
    align = paragraph.alignment
    if align is None:
        style = paragraph.style
        seen = set()
        while style is not None and id(style) not in seen:
            seen.add(id(style))
            if getattr(style, "paragraph_format", None) is not None and style.paragraph_format.alignment is not None:
                align = style.paragraph_format.alignment
                break
            style = getattr(style, "base_style", None)
    return _ALIGNMENT_TO_STR.get(align)


def _has_key_value_pattern(text: str) -> bool:
    return bool(KEY_VALUE_RE.match(text))


def _classify_keep_kind(reasons: list[str], element) -> str:
    if element.tag == qn("w:sectPr") or "section_break" in reasons or "section_properties" in reasons:
        return "section_break"
    if "table" in reasons or element.tag == qn("w:tbl"):
        return "table"
    if reasons == ["empty_paragraph"]:
        return "empty"
    if "tracked_change" in reasons or "track_changes" in reasons:
        return "track_changes"
    for key in ("image", "drawing", "field", "footnote", "hyperlink"):
        if key in reasons:
            return key
    return "other"


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
        os.makedirs(IMG_DIR, exist_ok=True)
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
            for override in num.findall(qn("w:lvlOverride")):
                if override.get(qn("w:ilvl")) == str(level):
                    fmt = override.find("./" + qn("w:lvl") + "/" + qn("w:numFmt"))
                    if fmt is not None:
                        return fmt.get(qn("w:val"))
            abstract = num.find(qn("w:abstractNumId"))
            abstract_id = abstract.get(qn("w:val")) if abstract is not None else None
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

    # numId e ilvl pueden proceder del párrafo o de su cadena de estilos.
    num_id = None
    level = None
    properties = [paragraph._p.pPr]
    properties.extend(style.element.pPr for style in _style_chain(paragraph.style))
    for p_pr in properties:
        num_pr = p_pr.numPr if p_pr is not None else None
        if num_pr is not None:
            if num_id is None and num_pr.numId is not None:
                num_id = num_pr.numId.val
            if level is None and num_pr.ilvl is not None:
                level = num_pr.ilvl.val
    if num_id == 0:  # Anulación explícita de numeración heredada.
        return info
    if num_id is not None:
        level = level if level is not None else 0
        fmt = _numbering_format(doc_part, num_id, level)
        info.update(is_list=True, level=level,
                    is_numbered=(fmt not in (None, "bullet")))
        return info

    style_name = paragraph.style.name if paragraph.style is not None else ""
    if style_name.startswith("List Bullet"):
        info["is_list"] = True
    elif style_name.startswith("List Number"):
        info.update(is_list=True, is_numbered=True)
    if info["is_list"]:
        suffix = re.search(r" (\d+)$", style_name)
        if suffix:
            info["level"] = min(int(suffix.group(1)) - 1, 8)
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


# ---------- Señales tipográficas y bloques opacos (Extractor v2) ----------
def _style_chain(style):
    """Recorre la herencia de estilos, incluso si un archivo trae un ciclo."""
    seen = set()
    while style is not None and style.style_id not in seen:
        seen.add(style.style_id)
        yield style
        style = style.base_style


def _effective_font_value(run, paragraph, attribute, default=None):
    value = getattr(run.font, attribute)
    if value is not None:
        return value
    for style in itertools.chain(_style_chain(run.style), _style_chain(paragraph.style)):
        value = getattr(style.font, attribute)
        if value is not None:
            return value
    return default


def _default_font_size(document):
    sizes = document.styles.element.xpath("./w:docDefaults/w:rPrDefault/w:rPr/w:sz/@w:val")
    return float(sizes[0]) / 2 if sizes else 11.0


def _run_size(run, paragraph, default_size):
    size = _effective_font_value(run, paragraph, "size")
    return size.pt if size is not None else default_size


def _extract_runs(paragraph):
    runs = []
    for run in paragraph.runs:
        if not run.text:
            continue
        underline = _effective_font_value(run, paragraph, "underline")
        runs.append(Run(
            text=run.text,
            bold=run.bold,
            italic=run.italic,
            underline=(bool(underline) if underline is not None else None),
            font=run.font.name,
            size=run.font.size.pt if run.font.size else None,
        ))
    return runs


def _left_indent_twips(paragraph):
    """Resuelve w:start/w:left por propiedad, sin confundirlo con w:hanging."""
    properties = [paragraph._p.pPr]
    properties.extend(style.element.pPr for style in _style_chain(paragraph.style))
    for p_pr in properties:
        if p_pr is None:
            continue
        ind = p_pr.find(qn("w:ind"))
        if ind is not None:
            for attr in ("w:start", "w:left"):
                value = ind.get(qn(attr))
                if value is not None:
                    return int(value)
    return 0


def _opaque_reasons(element, field_depth=0):
    if element.tag == qn("w:tbl"):
        return ["table"]
    if element.tag == qn("w:sectPr"):
        return ["section_properties"]
    if element.tag != qn("w:p"):
        if element.tag in {qn(f"w:{name}") for name in ("ins", "del", "moveFrom", "moveTo")}:
            return ["tracked_change"]
        return ["unknown_element"]

    tags = {node.tag for node in element.iter()}
    reasons = []
    image = qn("a:blip") in tags or "{urn:schemas-microsoft-com:vml}imagedata" in tags
    if image:
        reasons.append("image")
    elif tags.intersection({qn("w:drawing"), qn("w:pict")}):
        reasons.append("drawing")
    if field_depth or tags.intersection({qn("w:fldSimple"), qn("w:fldChar"), qn("w:instrText")}):
        reasons.append("field")
    if tags.intersection({qn("w:footnoteReference"), qn("w:endnoteReference")}):
        reasons.append("footnote")
    if qn("w:hyperlink") in tags:
        reasons.append("hyperlink")
    if tags.intersection({qn(f"w:{name}") for name in (
        "ins", "del", "moveFrom", "moveTo", "pPrChange", "rPrChange",
        "moveFromRangeStart", "moveFromRangeEnd", "moveToRangeStart", "moveToRangeEnd",
    )}):
        reasons.append("tracked_change")
    if qn("w:sectPr") in tags:
        reasons.append("section_break")
    # Estos elementos no se pueden representar con runs de texto plano.
    if tags.intersection({qn(name) for name in (
        "w:object", "w:sdt", "w:sym", "m:oMath", "m:oMathPara",
    )} | {"{http://schemas.openxmlformats.org/markup-compatibility/2006}AlternateContent"}):
        reasons.append("unknown_element")
    if not reasons:
        paragraph_children = {qn(name) for name in ("w:pPr", "w:r")}
        run_children = {qn(name) for name in (
            "w:rPr", "w:t", "w:tab", "w:br", "w:cr", "w:lastRenderedPageBreak",
        )}
        if any(child.tag not in paragraph_children for child in element) or any(
            child.tag not in run_children
            for run in element.findall(qn("w:r")) for child in run
        ):
            reasons.append("unknown_element")
    return reasons


def extract_document(path) -> DI:
    """Extrae el DI sin escribir imágenes ni modificar el DOCX de origen.

    Acepta rutas y streams binarios. Los IDs usan el índice real (base cero)
    de cada hijo del body; también se conservan vacíos y el sectPr final.
    El tamaño base es la moda ponderada por caracteres de los párrafos de
    texto editables. Se resuelven tamaños heredados y docDefaults (11 pt si
    no hay ninguno). En empates se conserva el primer tamaño encontrado.
    """
    if isinstance(path, Document):
        document = path
    else:
        if hasattr(path, "seek"):
            path.seek(0)
        document = docx.Document(os.fspath(path) if isinstance(path, PathLike) else path)

    default_size = _default_font_size(document)
    records = []
    sizes = Counter()
    indents = set()
    field_depth = 0
    for index, element in enumerate(document.element.body):
        paragraph = Paragraph(element, document) if element.tag == qn("w:p") else None
        reasons = _opaque_reasons(element, field_depth)
        for field in element.iter(qn("w:fldChar")):
            kind = field.get(qn("w:fldCharType"))
            if kind == "begin":
                field_depth += 1
            elif kind == "end":
                field_depth = max(0, field_depth - 1)
        if paragraph is not None and not reasons and not paragraph.text.strip():
            reasons = ["empty_paragraph"]
        records.append((index, element, paragraph, reasons))
        if paragraph is not None and not reasons:
            indent = _left_indent_twips(paragraph)
            if indent > 0:
                indents.add(indent)
            for run in paragraph.runs:
                if run.text:
                    sizes[_run_size(run, paragraph, default_size)] += len(run.text)

    base_size = sizes.most_common(1)[0][0] if sizes else default_size
    # Rangos relativos de las sangrías positivas: no se presupone un paso fijo.
    indent_levels = {value: level for level, value in enumerate(sorted(indents), start=1)}
    blocks = []
    opaque_reasons = {}
    total_records = len(records)
    for rec_pos, (index, element, paragraph, reasons) in enumerate(records):
        block_id = f"b{index}"
        if reasons:
            opaque_reasons[block_id] = reasons
            blocks.append(SourceBlock(
                id=block_id, type="keep",
                keep_kind=_classify_keep_kind(reasons, element),
                opaque_reasons=reasons,
                xml=etree.tostring(element, encoding="unicode", with_tail=False),
                text=paragraph.text if paragraph is not None else None,
            ))
            continue

        blank_before = 0
        cursor = rec_pos - 1
        while cursor >= 0 and records[cursor][3] == ["empty_paragraph"]:
            blank_before += 1
            cursor -= 1

        blank_after = 0
        cursor = rec_pos + 1
        while cursor < total_records and records[cursor][3] == ["empty_paragraph"]:
            blank_after += 1
            cursor += 1

        text = paragraph.text
        runs = [run for run in paragraph.runs if run.text]
        text_runs = [run for run in runs if run.text.strip()]
        list_info = detect_list_info(paragraph, document.part)
        indent = _left_indent_twips(paragraph)
        tab_count = max(text.count("\t"), len(element.findall(".//" + qn("w:tab"))))
        hints = Hints(
            all_bold=bool(text_runs) and all(
                bool(_effective_font_value(run, paragraph, "bold", False)) for run in text_runs
            ),
            is_all_caps=_is_all_caps(text),
            size_ratio=max(_run_size(run, paragraph, default_size) for run in runs) / base_size,
            words=len(text.split()),
            ends_with_period=text.rstrip().endswith("."),
            starts_with_glyph=bool(GLYPH_RE.match(text)),
            manual_numbering=bool(MANUAL_NUMBERING_RE.match(text)),
            indent_level=indent_levels.get(indent, 0),
            indent_cm=indent * 2.54 / 1440,
            alignment=_paragraph_alignment(paragraph),
            blank_lines_before=blank_before,
            blank_lines_after=blank_after,
            tab_count=tab_count,
            has_key_value_pattern=_has_key_value_pattern(text),
            style_name=paragraph.style.name,
            is_native_list=list_info["is_list"],
            is_list=list_info["is_list"],
            is_numbered=list_info["is_numbered"],
            list_level=list_info["level"],
        )
        blocks.append(SourceBlock(
            id=block_id, type="paragraph", text=text, runs=_extract_runs(paragraph),
            hints=hints, style_name=paragraph.style.name, list_info=list_info,
        ))

    return DI(
        blocks=blocks, base_font_size=base_size,
        stats=ExtractionStats(
            total_blocks=len(blocks), text_blocks=len(blocks) - len(opaque_reasons),
            opaque_blocks=len(opaque_reasons), opaque_reasons=opaque_reasons,
        ),
    )


# ---------- Adaptador para /extract/ y el rebuilder v1 ----------
def extract_structure(file_obj):
    """Mantiene el contrato v1 de párrafos, imágenes y tablas sobre el DI v2.

    Los keep se proyectan al formato anterior cuando son párrafos o tablas.
    Esta vista heredada no sustituye la preservación del XML ofrecida por el DI.
    """
    document = docx.Document(os.fspath(file_obj) if isinstance(file_obj, PathLike) else file_obj)
    intermediate = extract_document(document)
    blocks = []
    for source, element in zip(intermediate.blocks, document.element.body):
        if element.tag == qn("w:p"):
            paragraph = Paragraph(element, document)
            images = detect_inline_images(paragraph, document.part)
            if not paragraph.text.strip() and not images:
                continue
            runs = source.runs if source.type == "paragraph" else _extract_runs(paragraph)
            blocks.append({
                "type": "paragraph", "style_name": paragraph.style.name,
                "text": paragraph.text,
                "runs": [run.model_dump(exclude={"color"}) for run in runs],
                "has_inline_image": images,
                "list_info": source.list_info or detect_list_info(paragraph, document.part),
            })
        elif element.tag == qn("w:tbl"):
            rows = extract_table(Table(element, document))
            blocks.append({
                "type": "table", "rows": rows,
                "data": [[cell["text"] for cell in row] for row in rows],
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

