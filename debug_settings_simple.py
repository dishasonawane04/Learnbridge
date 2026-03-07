import os
from dotenv import load_dotenv

load_dotenv()
print(f"ENV OLLAMA_BASE_URL: {os.environ.get('OLLAMA_BASE_URL')}")

# Try to see what settings.py would resolve to
import sys
sys.path.append('.')
from learnbridge import settings
print(f"SETTINGS OLLAMA_BASE_URL: {getattr(settings, 'OLLAMA_BASE_URL', 'Not Set')}")
