import json
import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)

from ai_core.ai_engine import get_hybrid_response_context

def chat_with_ai(prompt, image_path=None, document_path=None, mode='text', stream=False, course_id=None):
    """
    Real AI response generator using local Ollama instance and RAG.
    """
    # Step 1: Get RAG context and system prompt
    context_text, system_prompt, is_course_aware = get_hybrid_response_context(prompt, course_id, mode=mode)
    
    # Step 2: Construct the final prompt for Ollama
    if context_text:
        final_prompt = f"{system_prompt}\n\nCONTEXT:\n{context_text}\n\nQUESTION: {prompt}"
    else:
        final_prompt = f"{system_prompt}\n\nQUESTION: {prompt}"

    url = f"{settings.OLLAMA_BASE_URL}/api/generate"
    # Default to settings model, switch to vision if image is present
    model = settings.OLLAMA_MODEL_TEXT
    if image_path:
        model = settings.OLLAMA_MODEL_VISION
    
    # Prepare Ollama request
    payload = {
        "model": model,
        "prompt": final_prompt,
        "stream": stream,
        "options": {
            "temperature": 0.5
        }
    }
    
    # Handle images if provided
    if image_path:
        try:
            import base64
            with open(image_path, "rb") as img_file:
                encoded_string = base64.b64encode(img_file.read()).decode('utf-8')
                payload["images"] = [encoded_string]
        except Exception as e:
            logger.error(f"Image encoding error: {e}")
            # Continue without image if encoding fails? Or return error?
            # Let's return error to be safe.
            if not stream: return f"Error processing image: {str(e)}"

    if stream:
        def generate():
            try:
                # Check connection before starting
                response = requests.post(url, json=payload, stream=True, timeout=90)
                response.raise_for_status()
                
                for line in response.iter_lines():
                    if line:
                        try:
                            chunk = json.loads(line.decode('utf-8'))
                            response_part = chunk.get('response', '')
                            if response_part:
                                yield response_part
                            if chunk.get('done'):
                                break
                        except json.JSONDecodeError:
                            continue
            except requests.exceptions.ConnectionError:
                yield "Error: Ollama is not running. Please start Ollama on your machine."
            except Exception as e:
                yield f"AI Stream Error: {str(e)}"
        
        return generate()
    else:
        try:
            response = requests.post(url, json=payload, timeout=60)
            response.raise_for_status()
            return response.json().get('response', "I failed to generate an answer.")
        except requests.exceptions.ConnectionError:
            return "Error: Ollama is not running. Please start Ollama on your machine."
        except Exception as e:
            return f"AI Error: {str(e)}"
