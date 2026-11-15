"""
Módulo de encabezados y títulos para templates_engine v2 (S3T12).
Aplica tamaño, negrita, alineación, espaciado anterior/posterior, color
y regla keep_with_next en títulos y estilos Heading.
"""

from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

ALIGN_MAP = {
    "left": WD_ALIGN_PARAGRAPH.LEFT,
    "center": WD_ALIGN_PARAGRAPH.CENTER,
    "right": WD_ALIGN_PARAGRAPH.RIGHT,
    "justify": WD_ALIGN_PARAGRAPH.JUSTIFY,
}


def _parse_rgb_color(color_str):
    if not color_str:
        return None
    hex_code = color_str.lstrip("#").strip()
    if len(hex_code) == 6:
        try:
            r = int(hex_code[0:2], 16)
            g = int(hex_code[2:4], 16)
            b = int(hex_code[4:6], 16)
            return RGBColor(r, g, b)
        except ValueError:
            return None
    return None


def apply_headings(doc, headings_config=None, heading_sizes=None):
    """
    Aplica configuración de títulos a encabezados del documento.
    Garantiza keep_with_next = True en todos los títulos.
    """
    # 1. Asegurar keep_with_next en estilos Heading del documento
    target_style_names = ["Heading 1", "Heading 2", "Heading 3", "Title", "Subtitle"]
    for s_name in target_style_names:
        if s_name in doc.styles:
            try:
                doc.styles[s_name].paragraph_format.keep_with_next = True
            except Exception:
                pass

    cfg_dict = {}
    if headings_config is not None:
        if hasattr(headings_config, "model_dump"):
            cfg_dict = headings_config.model_dump(exclude_none=True)
        elif isinstance(headings_config, dict):
            cfg_dict = headings_config

    for p in doc.paragraphs:
        style_name = p.style.name if p.style else ""
        key = None
        if "Heading 1" in style_name:
            key = "h1"
        elif "Heading 2" in style_name:
            key = "h2"
        elif "Heading 3" in style_name:
            key = "h3"
        elif "Title" in style_name:
            key = "title"

        is_heading = key is not None or style_name.startswith("Heading") or style_name == "Title"
        if is_heading:
            # Requisito 3: Aplicar keep_with_next a los títulos
            p.paragraph_format.keep_with_next = True

            item_cfg = cfg_dict.get(key, {}) if key else {}
            if isinstance(item_cfg, dict) and item_cfg:
                # Negrita
                bold = item_cfg.get("bold")
                if bold is not None:
                    for r in p.runs:
                        r.bold = bold

                # Cursiva
                italic = item_cfg.get("italic")
                if italic is not None:
                    for r in p.runs:
                        r.italic = italic

                # Alineación
                align_str = item_cfg.get("align")
                if align_str and align_str.lower() in ALIGN_MAP:
                    p.alignment = ALIGN_MAP[align_str.lower()]

                # Espaciado anterior / posterior
                space_before = item_cfg.get("space_before_pt")
                if space_before is not None:
                    p.paragraph_format.space_before = Pt(space_before)

                space_after = item_cfg.get("space_after_pt")
                if space_after is not None:
                    p.paragraph_format.space_after = Pt(space_after)

                # Tamaño en puntos
                size_pt = item_cfg.get("size_pt")
                if size_pt is not None:
                    for r in p.runs:
                        r.font.size = Pt(size_pt)

                # Color
                color_val = item_cfg.get("color")
                rgb = _parse_rgb_color(color_val)
                if rgb is not None:
                    for r in p.runs:
                        r.font.color.rgb = rgb

