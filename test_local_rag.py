import os
import django
import sys

sys.path.append('d:\\DISHA\\learnbridge')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'learnbridge.settings')
django.setup()

from django.conf import settings
from langchain_community.chat_models import ChatOllama
from langchain_huggingface.embeddings import HuggingFaceEmbeddings
import time

def test_ollama():
    print("Testing ChatOllama...")
    try:
        llm = ChatOllama(
            model=settings.OLLAMA_MODEL_TEXT,
            base_url=settings.OLLAMA_BASE_URL,
            temperature=0.1
        )
        resp = llm.invoke("Say 'Hello RAG' if you can hear me.")
        print(f"Ollama Response: {resp.content}")
        return True
    except Exception as e:
        print(f"Ollama Failed: {e}")
        return False

def test_embeddings():
    print("Testing HuggingFaceEmbeddings...")
    try:
        emb = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
        vec = emb.embed_query("This is a test sentence.")
        print(f"Embedding successful. Vector length: {len(vec)}")
        return True
    except Exception as e:
        print(f"Embeddings Failed: {e}")
        return False

if __name__ == "__main__":
    if test_ollama() and test_embeddings():
        print("ALL TESTS PASSED")
    else:
        print("TESTS FAILED")
