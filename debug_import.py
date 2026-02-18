try:
    import sentence_transformers
    print("sentence_transformers imported successfully")
except ImportError as e:
    print(f"Error importing sentence_transformers: {e}")

try:
    from langchain_community.embeddings import HuggingFaceEmbeddings
    print("HuggingFaceEmbeddings imported successfully")
    emb = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    print("Model loaded successfully")
except Exception as e:
    print(f"Error loading HF embeddings: {e}")
