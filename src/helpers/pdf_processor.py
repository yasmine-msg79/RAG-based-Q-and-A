# pdf text extraction module
from pypdf import PdfReader
import pytesseract
from PIL import Image
import fitz
import io
from langchain_text_splitters import RecursiveCharacterTextSplitter
# get the pdf text from the pdf file

def get_pdf_text(pdf_file):
    pdf_reader = PdfReader(pdf_file)
    pdf_document = fitz.open(pdf_file)

    text = []
    page_count = len(pdf_reader.pages)

    try:
        for index, page in enumerate(pdf_reader.pages):
            page_text = page.extract_text() or ""

            if not page_text.strip():
                pixmap = pdf_document[index].get_pixmap()
                image = Image.open(io.BytesIO(pixmap.tobytes("png")))
                page_text = get_ocr(image)

            text.append(page_text)

    finally:
        pdf_document.close()

    return "\n".join(text), page_count


def get_ocr(image):
    return pytesseract.image_to_string(image)


def chunk_text(text, chunk_size=1000, overlap=150):
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=overlap,
    )
    return text_splitter.split_text(text)
