"""
Módulo de formato de tablas para templates_engine v2 (S3T12).
Aplica estilo de tabla, bordes limpios OOXML, negrita y sombreado en encabezado,
sombreado alternado opcional (zebra) e interlineado específico para celdas.
"""

import re
from docx.shared import Pt, RGBColor
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls

_HEX_COLOR_RE = re.compile(r"^[0-9A-Fa-f]{6}$")


def _apply_table_borders(table, border_style: str, border_color: str):
    """Aplica bordes OOXML limpios sin depender de estilos instalados en el .docx original."""
    hex_color = str(border_color or "BFBFBF").lstrip("#").strip()
    if not _HEX_COLOR_RE.match(hex_color):
        hex_color = "BFBFBF"

    tblPr = table._tbl.tblPr
    if tblPr is None:
        return
    for old in tblPr.xpath("./w:tblBorders"):
        tblPr.remove(old)

    if border_style == "academic":
        # Estilo APA 7: solo líneas horizontales superior/inferior sin bordes verticales
        borders_xml = (
            f'<w:tblBorders {nsdecls("w")}>'
            f'<w:top w:val="single" w:sz="10" w:space="0" w:color="{hex_color}"/>'
            f'<w:bottom w:val="single" w:sz="10" w:space="0" w:color="{hex_color}"/>'
            f'<w:left w:val="none"/>'
            f'<w:right w:val="none"/>'
            f'<w:insideH w:val="none"/>'
            f'<w:insideV w:val="none"/>'
            f'</w:tblBorders>'
        )
    else:
        # Cuadrícula limpia moderna (Reporte ejecutivo / Personalizado)
        borders_xml = (
            f'<w:tblBorders {nsdecls("w")}>'
            f'<w:top w:val="single" w:sz="6" w:space="0" w:color="{hex_color}"/>'
            f'<w:bottom w:val="single" w:sz="6" w:space="0" w:color="{hex_color}"/>'
            f'<w:left w:val="single" w:sz="4" w:space="0" w:color="{hex_color}"/>'
            f'<w:right w:val="single" w:sz="4" w:space="0" w:color="{hex_color}"/>'
            f'<w:insideH w:val="single" w:sz="4" w:space="0" w:color="{hex_color}"/>'
            f'<w:insideV w:val="single" w:sz="4" w:space="0" w:color="{hex_color}"/>'
            f'</w:tblBorders>'
        )
    tblPr.append(parse_xml(borders_xml))


def _set_cell_shading(cell, hex_code: str):
    tcPr = cell._tc.get_or_add_tcPr()
    for old_shd in tcPr.xpath("./w:shd"):
        tcPr.remove(old_shd)
    tcPr.append(parse_xml(f'<w:shd {nsdecls("w")} w:fill="{hex_code}"/>'))


def apply_tables(doc, tables_config=None):
    """
    Aplica formato de tablas: estilo, bordes OOXML, negrita en fila de encabezado,
    sombreado de encabezado, filas alternadas opcionales e interlineado de celda.
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
    header_text_color = cfg.get("header_text_color")
    zebra_fill = cfg.get("zebra_fill")
    border_style = cfg.get("border_style")
    border_color = cfg.get("border_color", "BFBFBF")
    cell_line_spacing = cfg.get("cell_line_spacing", 1.0)

    header_rgb = None
    if header_text_color:
        hc = str(header_text_color).lstrip("#").strip()
        if _HEX_COLOR_RE.match(hc):
            header_rgb = RGBColor(int(hc[0:2], 16), int(hc[2:4], 16), int(hc[4:6], 16))

    valid_zebra = None
    if zebra_fill:
        zf = str(zebra_fill).lstrip("#").strip()
        if _HEX_COLOR_RE.match(zf):
            valid_zebra = zf

    for table in doc.tables:
        if table_style:
            try:
                table.style = table_style
            except Exception:
                pass

        if border_style in ("grid", "academic"):
            _apply_table_borders(table, border_style, border_color)

        # 1. Interlineado de celda, espaciado compacto y sombreado zebra en filas de datos
        for row_idx, row in enumerate(table.rows):
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    paragraph.paragraph_format.line_spacing = cell_line_spacing
                    paragraph.paragraph_format.space_before = Pt(2)
                    paragraph.paragraph_format.space_after = Pt(2)
                if valid_zebra and row_idx > 0 and row_idx % 2 == 0:
                    _set_cell_shading(cell, valid_zebra)

        # 2. Formato especial de fila de encabezado (fila 0)
        if len(table.rows) > 0:
            header_row = table.rows[0]

            for cell in header_row.cells:
                if header_bold or header_rgb is not None:
                    for paragraph in cell.paragraphs:
                        for run in paragraph.runs:
                            if header_bold:
                                run.bold = True
                            if header_rgb is not None:
                                run.font.color.rgb = header_rgb

                if header_fill:
                    hex_code = str(header_fill).lstrip("#").strip()
                    if _HEX_COLOR_RE.match(hex_code):
                        _set_cell_shading(cell, hex_code)

                if border_style == "academic":
                    hc = str(border_color or "333333").lstrip("#").strip()
                    if not _HEX_COLOR_RE.match(hc):
                        hc = "333333"
                    tcPr = cell._tc.get_or_add_tcPr()
                    for old_bdr in tcPr.xpath("./w:tcBorders"):
                        tcPr.remove(old_bdr)
                    tcPr.append(parse_xml(
                        f'<w:tcBorders {nsdecls("w")}>'
                        f'<w:bottom w:val="single" w:sz="6" w:space="0" w:color="{hc}"/>'
                        f'</w:tcBorders>'
                    ))

