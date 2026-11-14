"""
Módulo de formato de listas para templates_engine v2 (S3T12).
Aplica sangría por nivel en elementos de lista (bullet y numeradas).
"""

from docx.shared import Inches


def apply_lists(doc, lists_config=None):
    """
    Aplica sangría configurada según el nivel de anidamiento de las listas.
    """
    if lists_config is None:
        return

    cfg = {}
    if hasattr(lists_config, "model_dump"):
        cfg = lists_config.model_dump(exclude_none=True)
    elif isinstance(lists_config, dict):
        cfg = lists_config

    indent_cm_per_level = cfg.get("indent_cm_per_level")
    if indent_cm_per_level is None:
        return

    for paragraph in doc.paragraphs:
        is_list = False
        level = 0

        num_pr = paragraph._p.xpath("./w:pPr/w:numPr")
        if num_pr:
            is_list = True
            ilvl_nodes = paragraph._p.xpath("./w:pPr/w:numPr/w:ilvl/@w:val")
            level = int(ilvl_nodes[0]) if ilvl_nodes else 0
        elif paragraph.style and "list" in paragraph.style.name.lower():
            is_list = True
            level = 0

        if is_list:
            indent_inches = ((level + 1) * indent_cm_per_level) / 2.54
            paragraph.paragraph_format.left_indent = Inches(indent_inches)

