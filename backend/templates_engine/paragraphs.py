"""
Módulo de formato de párrafos para templates_engine v2 (S3T12).
Aplica alineación (left|justify), sangría de primera línea, espacio posterior
y estilos de callouts/citas en párrafos del cuerpo.
"""

import re
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls

_HEX_COLOR_RE = re.compile(r"^[0-9A-Fa-f]{6}$")

ALIGN_MAP = {
    "left": WD_ALIGN_PARAGRAPH.LEFT,
    "justify": WD_ALIGN_PARAGRAPH.JUSTIFY,
    "center": WD_ALIGN_PARAGRAPH.CENTER,
    "right": WD_ALIGN_PARAGRAPH.RIGHT,
}


def _is_heading(paragraph):
    style_name = paragraph.style.name if paragraph.style else ""
    return style_name.startswith("Heading") or style_name in ["Title", "Subtitle"]


def _is_list(paragraph):
    if paragraph._p.xpath("./w:pPr/w:numPr"):
        return True
    style_name = paragraph.style.name.lower() if paragraph.style else ""
    return "list" in style_name


def _is_callout(paragraph):
    style_name = paragraph.style.name.lower() if paragraph.style else ""
    return any(w in style_name for w in ["quote", "cita", "callout"])


def apply_paragraphs(doc, paragraph_config=None, callout_config=None):
    """
    Aplica sangría, alineación y espaciado a los párrafos del cuerpo del documento.
    """
    p_cfg = {}
    if paragraph_config is not None:
        if hasattr(paragraph_config, "model_dump"):
            p_cfg = paragraph_config.model_dump(exclude_none=True)
        elif isinstance(paragraph_config, dict):
            p_cfg = paragraph_config

    c_cfg = {}
    if callout_config is not None:
        if hasattr(callout_config, "model_dump"):
            c_cfg = callout_config.model_dump(exclude_none=True)
        elif isinstance(callout_config, dict):
            c_cfg = callout_config

    # Valores de párrafo regular
    alignment_str = p_cfg.get("alignment")
    first_line_indent_cm = p_cfg.get("first_line_indent_cm")
    space_after_pt = p_cfg.get("space_after_pt")
    space_before_pt = p_cfg.get("space_before_pt")

    for paragraph in doc.paragraphs:
        # No alterar títulos ni elementos de lista con sangría de primera línea de cuerpo
        if _is_heading(paragraph):
            continue

        if _is_callout(paragraph) and c_cfg:
            # Formato de callout / cita destacada
            if c_cfg.get("italic"):
                for r in paragraph.runs:
                    r.italic = True

            left_indent_cm = c_cfg.get("left_indent_cm")
            if left_indent_cm is not None:
                paragraph.paragraph_format.left_indent = Inches(left_indent_cm / 2.54)

            right_indent_cm = c_cfg.get("right_indent_cm", 0.5)
            if right_indent_cm is not None:
                paragraph.paragraph_format.right_indent = Inches(right_indent_cm / 2.54)

            paragraph.paragraph_format.space_before = Pt(c_cfg.get("space_before_pt", 8.0))
            paragraph.paragraph_format.space_after = Pt(c_cfg.get("space_after_pt", 8.0))

            pPr = paragraph._p.get_or_add_pPr()
            fill_color = c_cfg.get("fill")
            if fill_color:
                hex_fill = str(fill_color).lstrip("#").strip()
                if _HEX_COLOR_RE.match(hex_fill):
                    for old_shd in pPr.xpath("./w:shd"):
                        pPr.remove(old_shd)
                    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{hex_fill}"/>')
                    pPr.append(shd)

            border_color = c_cfg.get("border_color")
            if border_color:
                hex_border = str(border_color).lstrip("#").strip()
                if _HEX_COLOR_RE.match(hex_border):
                    for old_bdr in pPr.xpath("./w:pBdr"):
                        pPr.remove(old_bdr)
                    bdr = parse_xml(
                        f'<w:pBdr {nsdecls("w")}>'
                        f'<w:left w:val="single" w:sz="24" w:space="10" w:color="{hex_border}"/>'
                        f'</w:pBdr>'
                    )
                    pPr.append(bdr)
            continue

        if _is_list(paragraph):
            # Listas solo pueden recibir space_after si se desea, pero no first_line_indent
            if space_after_pt is not None:
                paragraph.paragraph_format.space_after = Pt(space_after_pt)
            continue

        # Párrafo de cuerpo normal
        if alignment_str and alignment_str.lower() in ALIGN_MAP:
            paragraph.alignment = ALIGN_MAP[alignment_str.lower()]

        if first_line_indent_cm is not None:
            # 1 pulgada = 2.54 cm
            paragraph.paragraph_format.first_line_indent = Inches(first_line_indent_cm / 2.54)

        if space_after_pt is not None:
            paragraph.paragraph_format.space_after = Pt(space_after_pt)

        if space_before_pt is not None:
            paragraph.paragraph_format.space_before = Pt(space_before_pt)

        # Si el párrafo inicia con un término/etiqueta en negrita ('Concepto: ...') y el preset
        # define accent_border_color, añadir una barra lateral sutil para separar bloques temáticos.
        accent_border = p_cfg.get("accent_border_color")
        if accent_border and paragraph.runs and paragraph.runs[0].bold and ":" in paragraph.runs[0].text:
            hex_accent = str(accent_border).lstrip("#").strip()
            if _HEX_COLOR_RE.match(hex_accent):
                pPr = paragraph._p.get_or_add_pPr()
                if not pPr.xpath("./w:pBdr"):
                    pPr.append(parse_xml(
                        f'<w:pBdr {nsdecls("w")}>'
                        f'<w:left w:val="single" w:sz="12" w:space="8" w:color="{hex_accent}"/>'
                        f'</w:pBdr>'
                    ))

