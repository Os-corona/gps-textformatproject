"""
Módulo de numeración de páginas para templates_engine v2 (S3T12).
Inserta campo de número de página dinámico (w:fldSimple w:instr="PAGE")
en la esquina superior derecha del encabezado de cada sección.
"""

from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls
from docx.enum.text import WD_ALIGN_PARAGRAPH


def apply_page_numbers(doc, enabled=False):
    """
    Inserta número de página en el encabezado de todas las secciones
    del documento si 'enabled' es True.
    """
    if not enabled:
        return

    for section in doc.sections:
        header = section.header
        has_page = False
        for p in header.paragraphs:
            if "PAGE" in p._p.xml:
                has_page = True
                break

        if not has_page:
            p = header.paragraphs[0] if header.paragraphs else header.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            run = p.add_run()
            fld_xml = f'<w:fldSimple {nsdecls("w")} w:instr="PAGE"/>'
            run._r.append(parse_xml(fld_xml))

