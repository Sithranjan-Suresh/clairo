import fitz

def extract_text_from_pdf(file_path: str) -> str:
    text = ""

    pdf_document = fitz.open(file_path)

    for page in pdf_document:
        text += page.get_text()

    pdf_document.close()

    return text