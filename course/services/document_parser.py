import os
import fitz  # PyMuPDF
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

_MIN_TEXT_CHARS = 100

_OCR_ERROR_MSG = (
    "Unable to detect text clearly. "
    "Please upload a clearer image or scan."
)


def _parse_pdf(file_path):
    """
    Extract text from PDF using PyMuPDF.
    Falls back to OCR (pytesseract via pdf2image) when extracted text is
    too short — which is the case for scanned / handwritten PDFs.
    Returns a list of dicts: [{'page_number': i, 'text': '...'}, ...]
    """
    pages = []
    with fitz.open(file_path) as doc:
        for i, page in enumerate(doc):
            pages.append({
                'page_number': i + 1,
                'text': page.get_text()
            })

    # Check total text across all pages
    total_text = "".join(p['text'] for p in pages).strip()

    # --- OCR Fallback for scanned / handwritten PDFs ---
    if len(total_text) < _MIN_TEXT_CHARS:
        logger.info(
            f"[OCR] PDF text too short ({len(total_text)} chars). "
            f"Attempting OCR fallback: {file_path}"
        )
        try:
            from course.utils.ocr_utils import ocr_pdf_pages
            ocr_text = ocr_pdf_pages(file_path)
            if ocr_text and len(ocr_text.strip()) >= _MIN_TEXT_CHARS:
                logger.info(f"[OCR] Fallback succeeded: {len(ocr_text)} chars extracted.")
                # Wrap the full OCR output as a single "page" to match expected structure
                return [{'page_number': 1, 'text': ocr_text}]
            else:
                logger.warning(f"[OCR] Fallback yielded insufficient text for: {file_path}")
                if not total_text:
                    return [{'page_number': 1, 'text': _OCR_ERROR_MSG}]
        except Exception as e:
            logger.error(f"[OCR] Fallback error for {file_path}: {e}")

    return pages

def _parse_docx(file_path):
    doc = Document(file_path)
    # Docx doesn't have strict pages like PDF, but we can treat it as one page or split by paragraphs
    text = "\n".join([para.text for para in doc.paragraphs])
    return [{'page_number': 1, 'text': text}]

def _parse_txt(file_path):
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        return [{'page_number': 1, 'text': f.read()}]
