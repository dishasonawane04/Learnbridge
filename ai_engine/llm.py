import requests
from django.conf import settings
import logging
import json

logger = logging.getLogger(__name__)

def ask_llm(prompt, system_prompt="You are a helpful educational assistant.", **kwargs):
    """
    Robust wrapper for Ollama that tries both 127.0.0.1 and localhost.
    Uses requests directly to avoid library-specific crashes.
    """
    # Try both common local endpoints for Windows stability
    base_url = getattr(settings, 'OLLAMA_BASE_URL', 'http://127.0.0.1:11434')
    urls = [
        f"{base_url}/api/chat",
        f"{base_url.replace('localhost', '127.0.0.1')}/api/chat",
        "http://127.0.0.1:11434/api/chat"
    ]
    
    # Deduplicate while preserving order
    urls = list(dict.fromkeys(urls))
    
    model = getattr(settings, 'OLLAMA_MODEL_TEXT', 'llama3.2:1b')
    options = {"temperature": 0.3}
    options.update(kwargs)
    
    # Extract format if present to place it at top level (Ollama requirement)
    format_type = options.pop('format', None)
    
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        "options": options,
        "stream": False
    }
    
    if format_type:
        payload["format"] = format_type

    last_error = None
    for url in urls:
        try:
            logger.info(f"Attempting AI request to {url}...")
            response = requests.post(url, json=payload, timeout=180)
            response.raise_for_status()
            data = response.json()
            return data.get("message", {}).get("content", "").strip()
        except Exception as e:
            last_error = str(e)
            logger.warning(f"AI attempt failed for {url}: {e}")
            continue
            
    error_msg = f"AI Error: Failed to connect to Ollama after trying {len(urls)} endpoints. Last error: {last_error}"
    logger.error(error_msg)
    return f"Error: {error_msg}"
