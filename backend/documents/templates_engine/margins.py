
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
        section.top_margin = Cm(margins_cm["top"])
        section.bottom_margin = Cm(margins_cm["bottom"])
        section.left_margin = Cm(margins_cm["left"])
        section.right_margin = Cm(margins_cm["right"])