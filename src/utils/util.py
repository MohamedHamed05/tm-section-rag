import os
import base64
import pathlib
import re
import pymupdf
from pdf2image import convert_from_path
from pathlib import Path
from io import BytesIO

def encode_image(image_path: str|pathlib.Path) -> str:
    """Encodes an image file to a base64 string."""
    with open(image_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
    return encoded_string

def parse_filename(filepath: str) -> dict:
    """
    Parses filenames following the pattern: {Subject}_{SectionNumber}_{SectionName}.pdf
    Example: 'Textmining_1_Case Study.pdf' →
        subject='Textmining', section_number=1, section_name='Case Study'
    """
    stem = Path(filepath).stem  # 'Textmining_1_Case Study'
    
    pattern = r"^([^_]+)_(\d+)_(.+)$"
    match = re.match(pattern, stem)
    
    if not match:
        # Graceful fallback — never crash the pipeline
        return {
            "subject": stem,
            "section_number": 0,
            "section_name": "unknown",
            "lecture_name": stem,
            "author": "unknown"
        }
    
    subject, section_number, section_name = match.groups()
    lecture_name = stem
    author_name = pymupdf.open(filepath).metadata.get("author", "unknown")

    return {
        "subject": subject,                  # 'Textmining'
        "section_number": int(section_number),  # 1
        "section_name": section_name,        # 'Case Study'
        "lecture_name": lecture_name,        # 'Textmining_1_Case Study'
        "author": author_name                # 'Name of the author from PDF metadata'
    }


def pdf_to_base64_images(pdf_path, dpi=200, fmt="JPEG", skip_first=True):
    """
    Convert a PDF into a list of base64-encoded images.

    Args:
        pdf_path (str): Path to the PDF file.
        dpi (int): Resolution for rendering.
        fmt (str): Image format ("PNG", "JPEG", etc.).
        skip_first (bool): Whether to skip the first page.

    Returns:
        List[str]: Base64-encoded images (one per page).
    """
    images = convert_from_path(pdf_path, dpi=dpi)
    base64_images = []
    
    for i, img in enumerate(images):
        if skip_first and i == 0:
            print(f"skipping first page ...")
            continue

        buffer = BytesIO()
        img.save(buffer, format=fmt)
        img_bytes = buffer.getvalue()
        encoded = base64.b64encode(img_bytes).decode("utf-8")
        base64_images.append(encoded)

    return base64_images