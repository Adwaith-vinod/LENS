import pymupdf
from docx import Document
from pathlib import Path


def extract_pdf(path):
    document = pymupdf.open(path)

    text = ""

    for page in document:
        text += page.get_text()

    return text


def extract_txt(path):
    with open(path, "r", encoding="utf-8") as file:
        return file.read()


def extract_docx(path):
    document = Document(path)

    text = ""

    for paragraph in document.paragraphs:
        text += paragraph.text + "\n"

    return text


def extract_text(path):
    path = Path(path)

    if path.suffix.lower() == ".pdf":
        return extract_pdf(path)

    elif path.suffix.lower() == ".txt":
        return extract_txt(path)

    elif path.suffix.lower() == ".docx":
        return extract_docx(path)

    else:
        return None




if __name__ == '__main__':

    file = "C:/Users/adwai/OneDrive/Documents/INTERNREPORT[1]_final_final.pdf"
    text = extract_text(file)

    print(text)