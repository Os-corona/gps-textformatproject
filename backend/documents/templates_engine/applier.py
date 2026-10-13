
from .margins import apply_margins
from .typography import apply_typography
from .spacing import apply_spacing


def apply_template(doc, config):
    margins_cm = {
        "top": config.margin_top,
        "bottom": config.margin_bottom,
        "left": config.margin_left,
        "right": config.margin_right,
    }

    apply_margins(doc, margins_cm)

    apply_typography(
        doc,
        config.font_name,
        config.font_size,
        getattr(config, "heading_sizes", None),
    )

    apply_spacing(doc, config.line_spacing)