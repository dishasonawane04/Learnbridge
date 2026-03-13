import fitz  # PyMuPDF
from pptx import Presentation
from PIL import Image
import os
import base64
from django.conf import settings

def extract_text_from_pdf(file_path):
    text = ""
    with fitz.open(file_path) as doc:
        for page in doc:
            text += page.get_text()
    return text

def extract_text_from_ppt(file_path):
    text = ""
    prs = Presentation(file_path)
    for slide in prs.slides:
        for shape in slide.shapes:
            if hasattr(shape, "text"):
                text += shape.text + "\n"
    return text

def extract_text_from_image(file_path):
    """Uses Ollama Vision model for OCR/Understanding"""
    import urllib.request
    import json
    try:
        with open(file_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
        
        url = f"{settings.OLLAMA_BASE_URL}/api/generate"
        data = json.dumps({
            "model": getattr(settings, "OLLAMA_MODEL_VISION", "llava:latest"),
            "prompt": "Transcribe all text from this image accurately. Only return the transcribed text.",
            "images": [encoded_string],
            "stream": False
        }).encode('utf-8')
        
        req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=180) as response:
            result = json.loads(response.read().decode('utf-8'))
            return result.get('response', '')
    except Exception as e:
        return f"Image OCR Failed: {str(e)}"

def extract_text_from_path(file_path):
    """Generic extraction based on file extension"""
    ext = os.path.splitext(file_path)[1].lower()
    
    if ext == '.pdf':
        return extract_text_from_pdf(file_path)
    elif ext in ['.pptx', '.ppt']:
        return extract_text_from_ppt(file_path)
    elif ext in ['.png', '.jpg', '.jpeg']:
        return extract_text_from_image(file_path)
    elif ext in ['.txt', '.md']:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
    else:
        return ""

def extract_content(material):
    """Main entry point to extract text based on material type"""
    text = extract_text_from_path(material.file.path)
    
    # Set file type based on extension (legacy logic)
    ext = os.path.splitext(material.file.path)[1].lower()
    if ext == '.pdf': material.file_type = 'pdf'
    elif ext in ['.pptx', '.ppt']: material.file_type = 'ppt'
    elif ext in ['.png', '.jpg', '.jpeg']: material.file_type = 'image'
    elif ext in ['.txt', '.md']: material.file_type = 'text'
        
    material.extracted_text = text
    material.save()
    return text
