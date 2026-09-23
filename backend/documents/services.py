import docx

def extract_paragraphs(file_object):
    """
    Recibe un archivo .docx y devuelve una lista con el texto de cada parrafo.
    Ignora los parrafos que solo contienen espacios o saltos de linea.
    """
    document = docx.Document(file_object)
    paragraphs = []

    for paragraph in document.paragraphs:
        text = paragraph.text.strip()
        if text:  # Ignorar párrafos vacíos
            paragraphs.append(text)

    return paragraphs