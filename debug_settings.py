import os
import django
from django.conf import settings

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'learnbridge.settings')
django.setup()

print(f"OLLAMA_BASE_URL: {settings.OLLAMA_BASE_URL}")
print(f"OLLAMA_MODEL_TEXT: {settings.OLLAMA_MODEL_TEXT}")

import requests
try:
    r = requests.get(f"{settings.OLLAMA_BASE_URL}/api/tags", timeout=5)
    print(f"Connection to OLLAMA_BASE_URL: {r.status_code}")
except Exception as e:
    print(f"Connection to OLLAMA_BASE_URL failed: {e}")

try:
    r = requests.get("http://127.0.0.1:11434/api/tags", timeout=5)
    print(f"Connection to 127.0.0.1: {r.status_code}")
except Exception as e:
    print(f"Connection to 127.0.0.1 failed: {e}")

try:
    r = requests.get("http://localhost:11434/api/tags", timeout=5)
    print(f"Connection to localhost: {r.status_code}")
except Exception as e:
    print(f"Connection to localhost failed: {e}")
