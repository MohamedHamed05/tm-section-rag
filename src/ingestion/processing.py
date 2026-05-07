import pymupdf
from utils.util import parse_filename, pdf_to_base64_images

def extract_pages_pymupdf(pdf_path: str, skip_first: bool = True) -> dict:
    """
    Extracts text and detects visuals from each page of a PDF.
    Returns a dict keyed by slide_number (1-indexed, title slide excluded by default).
    """
    doc = pymupdf.open(pdf_path)
    metadata = parse_filename(pdf_path)
    pages = {}
    base64_images = pdf_to_base64_images(pdf_path, skip_first=skip_first)
    

    for i, page in enumerate(doc):
        if skip_first and i == 0:
            continue

        slide_number = i + 1

        pages[slide_number] = {
            "text": page.get_text().strip(),
            'metadata': {'slide_txt': page.get_text().strip(), 'slide_number': i + 1, 'pdf_path': pdf_path, **metadata}
        }

    return pages

