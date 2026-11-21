from copy import deepcopy
from io import BytesIO
from os import PathLike, fspath

from docx import Document
from docx.document import Document as DocumentObject
from docx.enum.style import WD_STYLE_TYPE
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt, Inches
from pydantic import BaseModel, TypeAdapter

from common.document_schema import OutBlock
from common.integrity import validate_tokens
from .extractor import extract_document
from .numbering import NativeLists


_OUTPUT_BLOCK = TypeAdapter(OutBlock)


class DocumentIntegrityError(ValueError):
    def __init__(self, report):
        self.report = report
        super().__init__("El documento reconstruido no conserva los tokens del DI.")


def _normalize_blocks(structured_di):
    if isinstance(structured_di, BaseModel):
        structured_di = structured_di.model_dump(exclude_none=True)
    blocks = structured_di.get("blocks") if isinstance(structured_di, dict) else structured_di
    if not isinstance(blocks, (list, tuple)):
        raise ValueError("structured_di debe contener una lista de bloques.")
    result = []
    for block in blocks:
        if not isinstance(block, (dict, BaseModel)):
            raise ValueError("Cada bloque debe ser un objeto con type y su contenido.")
        data = block.model_dump(exclude_none=True) if isinstance(block, BaseModel) else dict(block)
        if data.get("type") == "paragraph" and not data.get("runs") and data.get("text"):
            data["runs"] = [{"text": data["text"]}]
        parsed = _OUTPUT_BLOCK.validate_python(data)
        if parsed.type == "image":
            raise ValueError("Las imágenes originales deben referenciarse mediante keep.")
        result.append(parsed)
    return result


def _element_text(element):
    """Texto de XML en orden de lectura, sin duplicar celdas combinadas."""
    if element.tag in {qn("w:t"), qn("w:delText"), qn("w:instrText")}:
        return element.text or ""
    if element.tag in {qn("w:tab"), qn("w:br"), qn("w:cr")}:
        return "\n"
    text = "".join(_element_text(child) for child in element)
    return text + ("\n" if element.tag in {qn("w:p"), qn("w:tc"), qn("w:tr")} else "")


def _keep_ids(block):
    return block.src or [block.id]


def _is_empty_paragraph_keep(source_block) -> bool:
    return source_block.type == "keep" and source_block.opaque_reasons == ["empty_paragraph"]


def _check_keep_references(blocks, originals, source_di):
    seen = []
    for block in blocks:
        if block.type != "keep":
            continue
        for source_id in _keep_ids(block):
            if source_id not in originals:
                raise ValueError(f"keep hace referencia a un bloque inexistente: {source_id}.")
            if source_id in seen:
                raise ValueError(f"keep duplicado: {source_id}.")
            seen.append(source_id)
    # Los bloques empty_paragraph no contienen tokens; la IA puede omitirlos
    # para evitar huecos redundantes, pero cualquier otro bloque opaco (imágenes,
    # tablas, saltos de sección, campos, etc.) es estrictamente obligatorio en orden.
    required = [
        block.id for block in source_di.blocks
        if block.type == "keep"
        and originals[block.id].tag != qn("w:sectPr")
        and not _is_empty_paragraph_keep(block)
    ]
    if [source_id for source_id in seen if source_id in required] != required:
        raise ValueError("Los bloques opacos deben aparecer una vez y en su orden original.")


def _expected_text(blocks, originals):
    texts = []
    for block in blocks:
        if block.type == "keep":
            texts.extend(_element_text(originals[source_id]) for source_id in _keep_ids(block))
        elif block.type == "table":
            for row in block.rows:
                for cell in row:
                    texts.append("".join(run.text for run in cell.runs) if cell.runs is not None else cell.text)
        else:
            texts.append("".join(run.text for run in block.runs))
    return "\n".join(texts)


def _paragraph_style(document, name):
    if name not in document.styles:
        style = document.styles.add_style(name, WD_STYLE_TYPE.PARAGRAPH)
        if name != "Normal":
            style.base_style = _paragraph_style(document, "Normal")
    return document.styles[name]


def _add_structured_runs(paragraph, runs):
    for source in runs:
        run = paragraph.add_run(source.text)
        for attribute in ("bold", "italic", "underline"):
            value = getattr(source, attribute)
            if value is not None:
                setattr(run, attribute, value)


def _configure_table_layout(table):
    """Aplica ancho 100%, márgenes internos de celda (tblCellMar) y cantSplit en filas."""
    tbl_pr = table._tbl.tblPr
    if tbl_pr is None:
        tbl_pr = OxmlElement("w:tblPr")
        table._tbl.insert(0, tbl_pr)

    # Ancho 100% (5000 en quintos de porcentaje según OOXML)
    for existing in tbl_pr.findall(qn("w:tblW")):
        tbl_pr.remove(existing)
    tbl_w = OxmlElement("w:tblW")
    tbl_w.set(qn("w:w"), "5000")
    tbl_w.set(qn("w:type"), "pct")
    tbl_pr.append(tbl_w)

    # Márgenes internos de celda para aire visual (en twips/dxa)
    for existing in tbl_pr.findall(qn("w:tblCellMar")):
        tbl_pr.remove(existing)
    cell_mar = OxmlElement("w:tblCellMar")
    for side, value in (("top", "60"), ("left", "108"), ("bottom", "60"), ("right", "108")):
        node = OxmlElement(f"w:{side}")
        node.set(qn("w:w"), value)
        node.set(qn("w:type"), "dxa")
        cell_mar.append(node)
    tbl_pr.append(cell_mar)


def _add_structured_table(document, block):
    width = sum(cell.h_span for cell in block.rows[0])
    table = document.add_table(rows=len(block.rows), cols=width)
    _configure_table_layout(table)
    if getattr(block, "header_row", True):
        header = OxmlElement("w:tblHeader")
        table.rows[0]._tr.get_or_add_trPr().append(header)
    for row_index, row in enumerate(block.rows):
        tr_pr = table.rows[row_index]._tr.get_or_add_trPr()
        if tr_pr.find(qn("w:cantSplit")) is None:
            tr_pr.append(OxmlElement("w:cantSplit"))
        column = 0
        for source in row:
            if source.v_merge is not None:
                raise ValueError("Las tablas con fusiones verticales deben conservarse con keep.")
            cell = table.cell(row_index, column)
            if source.h_span > 1:
                cell = cell.merge(table.cell(row_index, column + source.h_span - 1))
            if source.runs is not None:
                _add_structured_runs(cell.paragraphs[0], source.runs)
            else:
                cell.text = source.text
            column += source.h_span
    return table


def rebuild_document(original_path, structured_di, *, collapse_empty_paragraphs: bool = False) -> DocumentObject:
    """Reconstruye sobre una copia del paquete original y valida el resultado.

    Acepta el DI del extractor, un AIChunkOutput, un diccionario con blocks o
    una lista de bloques. keep resuelve src (o id) exclusivamente contra el
    body original; conserva las relaciones del paquete sin archivos temporales.

    Si collapse_empty_paragraphs=True, omite bloques keep cuya única razón sea
    'empty_paragraph' (sin tokens) para delegar el espaciado a la plantilla.
    """
    if isinstance(original_path, DocumentObject):
        buffer = BytesIO()
        original_path.save(buffer)
        buffer.seek(0)
        document = Document(buffer)
    else:
        if hasattr(original_path, "seek"):
            original_path.seek(0)
        document = Document(fspath(original_path) if isinstance(original_path, PathLike) else original_path)
    originals = {f"b{index}": element for index, element in enumerate(document.element.body)}
    source_di = extract_document(document)
    empty_keep_ids = {block.id for block in source_di.blocks if _is_empty_paragraph_keep(block)}
    blocks = _normalize_blocks(structured_di)
    if collapse_empty_paragraphs:
        blocks = [
            block for block in blocks
            if not (block.type == "keep" and all(sid in empty_keep_ids for sid in _keep_ids(block)))
        ]
    _check_keep_references(blocks, originals, source_di)
    expected = _expected_text(blocks, originals)

    body = document.element.body
    body.clear_content()
    final_section = body.get_or_add_sectPr()
    lists = NativeLists(document)
    for block in blocks:
        if block.type != "list_item":
            lists.reset()
        if block.type == "keep":
            for source_id in _keep_ids(block):
                element = originals[source_id]
                if element.tag != qn("w:sectPr"):
                    final_section.addprevious(deepcopy(element))
        elif block.type == "table":
            _add_structured_table(document, block)
        else:
            style = "Normal"
            if block.type == "heading":
                style = "Title" if block.level == 0 else f"Heading {block.level}"
            elif block.type == "callout":
                style = "Quote" if block.kind == "quote" else "Intense Quote"
            paragraph = document.add_paragraph(style=_paragraph_style(document, style))
            _add_structured_runs(paragraph, block.runs)
            if block.type == "list_item":
                lists.apply(paragraph, block)

    buffer = BytesIO()
    document.save(buffer)
    buffer.seek(0)
    reopened = Document(buffer)
    report = validate_tokens(
        expected, _element_text(reopened.element.body),
        source_blocks=len(blocks), out_blocks=len(reopened.element.body),
    )
    if not report.is_valid:
        raise DocumentIntegrityError(report)
    return reopened


def apply_runs(paragraph, runs):
    for run_data in runs:
        run = paragraph.add_run(run_data["text"])

        if run_data.get("bold"):
            run.bold = True

        if run_data.get("italic"):
            run.italic = True

        if run_data.get("underline") is not None:
            run.underline = run_data["underline"]

        if run_data.get("font"):
            run.font.name = run_data["font"]

        if run_data.get("size"):
            run.font.size = Pt(run_data["size"])


def add_image_to_paragraph(paragraph, image_path, width_inches=None):
    run = paragraph.add_run()

    if width_inches:
        run.add_picture(image_path, width=Inches(width_inches))
    else:
        run.add_picture(image_path)


def apply_list_style(doc, paragraph, list_info):
    if not list_info or not list_info.get("is_list"):
        return

    # Distingue entre listas numeradas y listas con viñetas.
    style_name = (
        "List Number"
        if list_info.get("is_numbered")
        else "List Bullet"
    )

    try:
        paragraph.style = doc.styles[style_name]
    except KeyError:
        pass


def add_table_to_doc(doc, table_data):
    rows = table_data["rows"]

    if not rows:
        return None

    num_rows = len(rows)
    num_cols = max(
        sum(cell.get("h_span", 1) for cell in row)
        for row in rows
    )

    table = doc.add_table(rows=num_rows, cols=num_cols)
    table.style = "Table Grid"

    for i, row in enumerate(rows):
        col = 0

        for cell_data in row:
            span = cell_data.get("h_span", 1)
            v_merge = cell_data.get("v_merge")
            cell = table.cell(i, col)

            if v_merge == "continue":
                table.cell(i - 1, col).merge(cell)
            else:
                if span > 1:
                    cell = cell.merge(
                        table.cell(i, col + span - 1)
                    )

                cell.text = cell_data.get("text", "")

            col += span

    return table


def add_tables_to_doc(doc, tables_data):
    for table_data in tables_data:
        add_table_to_doc(doc, table_data)

    return doc


def rebuild_from_structure(blocks, config=None):
    """
    Reconstruye un documento Word a partir de una lista de bloques.

    Args:
        blocks: Lista de bloques con párrafos y tablas.
        config: Configuración opcional de TemplateConfig.
                Si se proporciona, aplica márgenes, tipografía
                e interlineado antes de devolver el documento.

    Returns:
        Documento de python-docx listo para guardarse.
    """
    doc = Document()

    for block in blocks:
        btype = block.get("type")

        if btype == "paragraph":
            paragraph = doc.add_paragraph()

            try:
                paragraph.style = doc.styles[block["style_name"]]
            except KeyError:
                pass

            apply_list_style(
                doc,
                paragraph,
                block.get("list_info"),
            )

            apply_runs(
                paragraph,
                block.get("runs", []),
            )

            images = block.get("has_inline_image")

            if images:
                for path in images:
                    add_image_to_paragraph(
                        paragraph,
                        path,
                        width_inches=4,
                    )

        elif btype == "table":
            add_table_to_doc(doc, block)

    # Aplicar la plantilla después de construir el documento.
    if config is not None:
        from templates_engine.applier import apply_template

        apply_template(doc, config)

    return doc

