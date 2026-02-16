import os
import fitz  # PyMuPDF
from docxtpl import DocxTemplate
from docx import Document
import logging

logger = logging.getLogger(__name__)

def parse_document(file_path):
    """
    Extracts text from PDF, DOCX, or TXT files.
    Returns a list of dicts: [{'page_number': i, 'text': '...'}, ...]
    """
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        return []

    ext = os.path.splitext(file_path)[1].lower()
    
    try:
        if ext == '.pdf':
            return _parse_pdf(file_path)
        elif ext == '.docx':
            return _parse_docx(file_path)
        elif ext in ['.txt', '.md']:
            return _parse_txt(file_path)
        else:
            raise ValueError(f"Unsupported file format: {ext}")
    except Exception as e:
        logger.error(f"Error parsing {file_path}: {e}")
        return []

def _parse_pdf(file_path):
    pages = []
    with fitz.open(file_path) as doc:
        for i, page in enumerate(doc):
            pages.append({
                'page_number': i + 1,
                'text': page.get_text()
            })
    return pages

def _parse_docx(file_path):
    doc = Document(file_path)
    # Docx doesn't have strict pages like PDF, but we can treat it as one page or split by paragraphs
    text = "\n".join([para.text for para in doc.paragraphs])
    return [{'page_number': 1, 'text': text}]

def _parse_txt(file_path):
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        return [{'page_number': 1, 'text': f.read()}]
