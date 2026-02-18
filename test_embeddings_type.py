import sys
import os

# Setup Django path just in case
sys.path.append('d:\\DISHA\\learnbridge')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'learnbridge.settings')

# Try avoiding django setup if possible, or accept if it works
try:
    from ai_engine.vector_store import get_embeddings_model, CustomHuggingFaceEmbeddings
    model = get_embeddings_model()
    print(f"Model Type: {type(model)}")
    print(f"Is Instance of Custom?: {isinstance(model, CustomHuggingFaceEmbeddings)}")
except Exception as e:
    print(f"Error: {e}")
