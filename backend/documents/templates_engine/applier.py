
from .margins import apply_margins
from .typography import apply_typography
from .spacing import apply_spacing


def apply_template(doc, config):
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

    apply_margins(doc, margins_cm)

    apply_typography(
        doc,
        font_name,
        font_size,
        heading_sizes,
    )

    apply_spacing(doc, line_spacing)