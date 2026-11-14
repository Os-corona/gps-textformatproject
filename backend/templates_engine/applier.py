from .margins import apply_margins
from .typography import apply_typography
from .spacing import apply_spacing
from .headings import apply_headings
from .paragraphs import apply_paragraphs
from .lists import apply_lists
from .tables import apply_tables
from .page_numbers import apply_page_numbers


def apply_template(doc, config):
    """
    Aplica una plantilla de formato a un documento DOCX.
    Orden de aplicación:
    1. Márgenes
    2. Tipografía base y estilos
    3. Interlineado general
    4. Encabezados y títulos (headings)
    5. Párrafos del cuerpo (sangrías, alineación, callouts)
    6. Listas (sangría por nivel)
    7. Tablas (estilo, encabezado, interlineado de celda)
    8. Numeración de páginas
    """
    if isinstance(config, dict):
        if "margins_cm" in config and isinstance(config["margins_cm"], dict):
            margins_cm = config["margins_cm"]
        else:
            margins_cm = {
                "top": config.get("margin_top", 2.54),
                "bottom": config.get("margin_bottom", 2.54),
                "left": config.get("margin_left", 2.54),
                "right": config.get("margin_right", 2.54),
            }
        font_name = config.get("font_family") or config.get("font_name", "Times New Roman")
        font_size = config.get("font_size_pt") or config.get("font_size", 12)
        heading_sizes = config.get("heading_sizes_pt") or config.get("heading_sizes", None)
        line_spacing = config.get("line_spacing", 1.5)

        headings_config = config.get("headings")
        paragraph_config = config.get("paragraph")
        callout_config = config.get("callout")
        lists_config = config.get("lists")
        tables_config = config.get("tables")
        page_numbers = config.get("page_numbers", False)
    else:
        if hasattr(config, "margins_cm") and config.margins_cm:
            margins_cm = config.margins_cm if isinstance(config.margins_cm, dict) else config.margins_cm.model_dump()
        else:
            margins_cm = {
                "top": getattr(config, "margin_top", 2.54),
                "bottom": getattr(config, "margin_bottom", 2.54),
                "left": getattr(config, "margin_left", 2.54),
                "right": getattr(config, "margin_right", 2.54),
            }
        font_name = getattr(config, "font_family", None) or getattr(config, "font_name", "Times New Roman")
        font_size = getattr(config, "font_size_pt", None) or getattr(config, "font_size", 12)
        heading_sizes = getattr(config, "heading_sizes_pt", None) or getattr(config, "heading_sizes", None)
        line_spacing = getattr(config, "line_spacing", 1.5)

        headings_config = getattr(config, "headings", None)
        paragraph_config = getattr(config, "paragraph", None)
        callout_config = getattr(config, "callout", None)
        lists_config = getattr(config, "lists", None)
        tables_config = getattr(config, "tables", None)
        page_numbers = getattr(config, "page_numbers", False)

    # 1. Márgenes
    apply_margins(doc, margins_cm)

    # 2. Tipografía base y estilos
    apply_typography(
        doc,
        font_name,
        font_size,
        heading_sizes,
    )

    # 3. Interlineado general de cuerpo
    apply_spacing(doc, line_spacing)

    # 4. Estilos y formato de encabezados (keep_with_next, bold, align, etc.)
    apply_headings(doc, headings_config, heading_sizes)

    # 5. Formato de párrafos de cuerpo (first_line_indent, alignment, callout)
    apply_paragraphs(doc, paragraph_config, callout_config)

    # 6. Formato de listas
    apply_lists(doc, lists_config)

    # 7. Formato de tablas e interlineado de celda (1.0)
    apply_tables(doc, tables_config)

    # 8. Numeración de página
    apply_page_numbers(doc, page_numbers)
