
from docx.enum.text import WD_LINE_SPACING
from docx.oxml.ns import qn


def _set_multiple_spacing(paragraph_format, line_spacing):
    """Fuerza la regla múltiple en el XML de Word."""
    paragraph_format.line_spacing = line_spacing

    p_pr = paragraph_format._element
    spacing = p_pr.get_or_add_pPr().get_or_add_spacing()

    # OOXML: 240 equivale a una línea; 360 equivale a 1.5.
    spacing.set(qn("w:line"), str(round(line_spacing * 240)))
    spacing.set(qn("w:lineRule"), "auto")


def apply_spacing(doc, line_spacing):
    """
    Aplica interlineado múltiple al estilo Normal y a los
    párrafos del cuerpo, excluyendo tablas, encabezados y pies.
    """
    _set_multiple_spacing(
        doc.styles["Normal"].paragraph_format,
        line_spacing,
    )

    for paragraph in doc.paragraphs:
        _set_multiple_spacing(
            paragraph.paragraph_format,
            line_spacing,
        )