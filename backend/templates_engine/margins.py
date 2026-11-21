from docx.shared import Cm


def apply_margins(doc, margins_cm):
    """
    Aplica los márgenes configurados a todas las secciones
    sin modificar la orientación ni el tamaño de página.

    Args:
        doc: Documento de python-docx.
        margins_cm: Diccionario con top, bottom, left y right.
    """
    for section in doc.sections:
        if margins_cm.get("top") is not None:
            section.top_margin = Cm(margins_cm["top"])
        if margins_cm.get("bottom") is not None:
            section.bottom_margin = Cm(margins_cm["bottom"])
        if margins_cm.get("left") is not None:
            section.left_margin = Cm(margins_cm["left"])
        if margins_cm.get("right") is not None:
            section.right_margin = Cm(margins_cm["right"])

