"""
Módulo de formato de tablas para templates_engine v2 (S3T12).
Aplica estilo de tabla, negrita en encabezado, sombreado de encabezado (fill)
e interlineado específico para celdas (por defecto 1.0).
"""

from docx.shared import Pt
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls


def apply_tables(doc, tables_config=None):
    """
    Aplica formato de tablas: estilo, negrita en fila de encabezado,
    sombreado de encabezado y fuerza el interlineado de celda (1.0 por defecto).
    """
    cfg = {}
    if tables_config is not None:
        if hasattr(tables_config, "model_dump"):
            cfg = tables_config.model_dump(exclude_none=True)
        elif isinstance(tables_config, dict):
            cfg = tables_config

    table_style = cfg.get("style")
    header_bold = cfg.get("header_bold", False)
    header_fill = cfg.get("header_fill")
    cell_line_spacing = cfg.get("cell_line_spacing", 1.0)

    for table in doc.tables:
        if table_style:
            try:
                table.style = table_style
            except Exception:
                pass

        # 1. Aplicar interlineado de celda a todos los párrafos de la tabla (Requisito 3)
        for row in table.rows:
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    paragraph.paragraph_format.line_spacing = cell_line_spacing

        # 2. Formato especial de fila de encabezado (fila 0)
        if len(table.rows) > 0:
            header_row = table.rows[0]

            for cell in header_row.cells:
                # Negrita en encabezado
                if header_bold:
                    for paragraph in cell.paragraphs:
                        for run in paragraph.runs:
                            run.bold = True

                # Sombreado de encabezado (w:shd)
                if header_fill:
                    hex_code = header_fill.lstrip("#")
                    tcPr = cell._tc.get_or_add_tcPr()
                    for old_shd in tcPr.xpath("./w:shd"):
                        tcPr.remove(old_shd)
                    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{hex_code}"/>')
                    tcPr.append(shd)

