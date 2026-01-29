import fitz  # PyMuPDF
from pptx import Presentation
from PIL import Image
import os
import requests
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
    try:
        with open(file_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
        
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": getattr(settings, "OLLAMA_MODEL_VISION", "llava:latest"),
                "prompt": "Transcribe all text from this image accurately. Only return the transcribed text.",
                "images": [encoded_string],
                "stream": False
            }
        )
        return response.json().get('response', '')
    except Exception as e:
        return f"Image OCR Failed: {str(e)}"

def extract_content(material):
    """Main entry point to extract text based on material type"""
    file_path = material.file.path
    ext = os.path.splitext(file_path)[1].lower()
    
    if ext == '.pdf':
        material.file_type = 'pdf'
        text = extract_text_from_pdf(file_path)
    elif ext in ['.pptx', '.ppt']:
        material.file_type = 'ppt'
        text = extract_text_from_ppt(file_path)
    elif ext in ['.png', '.jpg', '.jpeg']:
        material.file_type = 'image'
        text = extract_text_from_image(file_path)
    elif ext in ['.txt', '.md']:
        material.file_type = 'text'
        with open(file_path, 'r') as f:
            text = f.read()
    else:
        text = "Unsupported file type"
        
    material.extracted_text = text
    material.save()
    return text
