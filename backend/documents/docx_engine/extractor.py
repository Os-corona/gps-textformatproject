import docx
from docx.document import Document
from docx.oxml.text.paragraph import CT_P
from docx.oxml.table import CT_Tbl
from docx.table import Table
from docx.text.paragraph import Paragraph

def extract_structure(file_obj):
    document = docx.Document(file_obj)
    blocks = []

    for block in iter_block_items(document):
        
        if isinstance(block, Paragraph):
            if not block.text.strip():
                continue
            
            runs_data = []
            for run in block.runs:
                if run.text:
                    runs_data.append({
                        "text": run.text,
                        "bold": run.bold,
                        "italic": run.italic,
                        "font": run.font.name,
                        "size": run.font.size.pt if run.font.size else None
                    })
            
            blocks.append({
                "type": "paragraph",
                "style_name": block.style.name,
                "text": block.text,
                "runs": runs_data
            })
            
        elif isinstance(block, Table):
            table_data = []
            for row in block.rows:
                row_data = [cell.text.strip() for cell in row.cells]
                table_data.append(row_data)
            
            blocks.append({
                "type": "table",
                "data": table_data
            })
            
    return blocks

def iter_block_items(parent):
    if isinstance(parent, Document):
        parent_elm = parent.element.body
    else:
        parent_elm = parent._element

    for child in parent_elm.iterchildren():
        if isinstance(child, CT_P):
            yield Paragraph(child, parent)
        elif isinstance(child, CT_Tbl):
            yield Table(child, parent)