import sys
import os

# Setup Django
sys.path.append('d:\\DISHA\\learnbridge')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'learnbridge.settings')
import django
django.setup()

from ai_engine.vector_store import get_embeddings_model
from langchain_community.vectorstores import FAISS

def test_faiss():
    print("Testing FAISS with Custom Embeddings...")
    embeddings = get_embeddings_model()
    print(f"Embeddings Model: {type(embeddings)}")

    texts = ["foo", "bar", "baz"]
    print("Creating vector store...")
    try:
        db = FAISS.from_texts(texts, embeddings)
        print("Vector store created successfully.")
    except Exception as e:
        print(f"FAILED to create vector store: {e}")
        # Print full traceback
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_faiss()
