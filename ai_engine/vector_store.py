import os
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

def create_vector_db(chunks, course_id):
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )
    
    db = FAISS.from_documents(chunks, embeddings)
    # Ensure directory exists
    os.makedirs(f"media/vector_db", exist_ok=True)
    db.save_local(f"media/vector_db/course_{course_id}")

def load_vector_db(course_id):
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )
    path = f"media/vector_db/course_{course_id}"
    if not os.path.exists(path):
        return None
    return FAISS.load_local(path, embeddings, allow_dangerous_deserialization=True)
