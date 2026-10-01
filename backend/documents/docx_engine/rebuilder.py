from docx import Document
from docx.shared import Pt

def rebuild_from_structure(blocks):
    doc = Document()

    for block in blocks:
        if block.get("type") == "paragraph":
            paragraph = doc.add_paragraph()

            try:
                paragraph.style = doc.styles[block["style_name"]]
            except KeyError:
                pass

            for run_data in block["runs"]:
                run = paragraph.add_run(run_data["text"])
                if run_data.get("bold"):
                    run.bold = True
                if run_data.get("italic"):
                    run.italic = True
                if run_data.get("font"):
                    run.font.name = run_data["font"]
                if run_data.get("size"):
                    run.font.size = Pt(run_data["size"])

        elif block.get("type") == "table":
            if block["data"]:
                rows = len(block["data"])
                cols = len(block["data"][0])
                table = doc.add_table(rows=rows, cols=cols)
                table.style = 'Table Grid'

                for i, row_data in enumerate(block["data"]):
                    for j, cell_text in enumerate(row_data):
                        table.cell(i, j).text = cell_text

    return doc