"""
ocr_utils.py — OCR fallback utilities for handwritten notes

This module provides:
  - Image preprocessing (grayscale + thresholding) to improve handwriting accuracy
  - ocr_image()      → runs pytesseract on a single image file or PIL Image
  - ocr_pdf_pages()  → converts PDF pages to images, runs OCR on each, aggregates text

These are ONLY used as fallbacks when normal extraction yields too little text.
All functions silently catch exceptions and return '' so callers are never broken.
"""

import os
import logging

logger = logging.getLogger(__name__)

# Minimum number of characters to consider OCR output "readable"
MIN_OCR_CHARS = 20

# --- Tesseract path (Windows). Adjust if installed elsewhere. ---
_TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


def _configure_tesseract():
    """Point pytesseract at the Tesseract binary (Windows)."""
    try:
        import pytesseract
        if os.path.exists(_TESSERACT_PATH):
            pytesseract.pytesseract.tesseract_cmd = _TESSERACT_PATH
    except ImportError:
        pass


def _preprocess_image(pil_image):
    """
    Convert to grayscale and apply binary thresholding.
    This significantly improves OCR accuracy on handwritten notes.
    Returns the processed PIL Image.
    """
    try:
        from PIL import ImageFilter, ImageOps
        # Convert to grayscale
        gray = pil_image.convert('L')
        # Apply a slight sharpening to make strokes cleaner
        sharpened = gray.filter(ImageFilter.SHARPEN)
        # Binary threshold: pixels < 128 → black, others → white
        thresholded = sharpened.point(lambda p: 255 if p > 128 else 0, '1')
        # Convert back to 'L' mode for tesseract compatibility
        return thresholded.convert('L')
    except Exception as e:
        logger.warning(f"[OCR] Preprocessing failed, using raw image: {e}")
        return pil_image


def ocr_image(image_input):
    """
    Run OCR on a single image (file path string or PIL Image).
    Returns extracted text string, or '' on any failure.
    """
    _configure_tesseract()
    try:
        import pytesseract
        from PIL import Image

        if isinstance(image_input, str):
            if not os.path.exists(image_input):
                logger.warning(f"[OCR] Image file not found: {image_input}")
                return ''
            img = Image.open(image_input)
        else:
            img = image_input  # already a PIL Image

        processed = _preprocess_image(img)
        try:
            text = pytesseract.image_to_string(processed, lang='eng+hin+mar')
        except pytesseract.pytesseract.TesseractError as te:
            logger.warning(f"[OCR] Multilingual OCR failed (missing traineddata?). Falling back to 'eng'. Error: {te}")
            text = pytesseract.image_to_string(processed, lang='eng')
            
        return text.strip()

    except ImportError:
        logger.warning("[OCR] pytesseract is not installed. Run: pip install pytesseract")
        return ''
    except Exception as e:
        logger.error(f"[OCR] ocr_image() failed: {e}")
        return ''


def ocr_pdf_pages(pdf_path):
    """
    Convert each page of a PDF to an image, then run OCR on each.
    Returns aggregated text string (all pages joined with newlines), or '' on failure.
    Uses PyMuPDF (fitz) to avoid requiring poppler-windows.
    """
    _configure_tesseract()
    try:
        import fitz
        from PIL import Image

        page_texts = []
        with fitz.open(pdf_path) as doc:
            for page in doc:
                # Render page to an image (zoom factor 2 roughly gives 144 DPI)
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                
                # Handling different color spaces
                if pix.n - pix.alpha == 3:  # RGB
                    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                elif pix.n - pix.alpha == 1:  # Grayscale
                    img = Image.frombytes("L", [pix.width, pix.height], pix.samples)
                else:
                    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

                text = ocr_image(img)
                if text:
                    page_texts.append(text)
                else:
                    page_texts.append('')

        return '\n\n'.join(page_texts).strip()

    except Exception as e:
        logger.error(f"[OCR] ocr_pdf_pages() failed for {pdf_path}: {e}")
        return ''


def is_text_sufficient(text, min_chars=100):
    """
    Returns True if the extracted text is long enough to be considered valid.
    Used to decide whether OCR fallback should be triggered.
    """
    return bool(text) and len(text.strip()) >= min_chars
