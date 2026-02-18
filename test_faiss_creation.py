import sys
import os

# Setup path
sys.path.append('d:\\DISHA\\learnbridge')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'learnbridge.settings')

from ai_engine.vector_store import get_embeddings_model
from langchain_community.vectorstores import FAISS

def test_creation():
    print("Testing FAISS creation...")
    embeddings = get_embeddings_model()
    texts = ["foo", "bar"]
    metadatas = [{"source": "test"}, {"source": "test"}]
    
    try:
        db = FAISS.from_texts(texts, embeddings, metadatas=metadatas)
        print("FAISS creation SUCCESS")
    except Exception as e:
        print(f"FAISS creation FAILED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_creation()
