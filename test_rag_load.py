import os
import django
import sys
import traceback

# Setup Django
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'learnbridge.settings')
django.setup()

from django.conf import settings
from ai_engine.vector_store import get_embeddings_model
from langchain_community.vectorstores import FAISS

def test_load():
    course_id = 5
    folder_path = os.path.join(settings.MEDIA_ROOT, 'vectorstore', f'course_{course_id}')
    print(f"Testing load from: {folder_path}")
    
    if not os.path.exists(folder_path):
        print("Folder does not exist.")
        return

    try:
        print("Initializing embeddings model...")
        embeddings = get_embeddings_model()
        print("Loading FAISS index...")
        db = FAISS.load_local(folder_path, embeddings, allow_dangerous_deserialization=True)
        print(f"Success! Vectors: {db.index.ntotal}")
    except Exception:
        print("--- LOAD ERROR ---")
        traceback.print_exc()

if __name__ == "__main__":
    test_load()
