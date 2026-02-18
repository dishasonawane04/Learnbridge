import torch
from transformers import AutoTokenizer, AutoModel
from typing import List
from langchain_core.embeddings import Embeddings
import os

class CustomHuggingFaceEmbeddings(Embeddings):
    def __init__(self, model_name="sentence-transformers/all-MiniLM-L6-v2"):
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModel.from_pretrained(model_name)

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        # Batch processing for efficiency? For simplicity, loop or small batches
        embeddings = []
        for text in texts:
            embeddings.append(self.embed_query(text))
        return embeddings

    def embed_query(self, text: str) -> List[float]:
        inputs = self.tokenizer(text, return_tensors="pt", padding=True, truncation=True)
        with torch.no_grad():
            outputs = self.model(**inputs)
            # Mean Pooling
            token_embeddings = outputs.last_hidden_state
            attention_mask = inputs['attention_mask']
            input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
            embedding = torch.sum(token_embeddings * input_mask_expanded, 1) / torch.clamp(input_mask_expanded.sum(1), min=1e-9)
            # Normalize
            embedding = torch.nn.functional.normalize(embedding, p=2, dim=1)
            return embedding[0].tolist()

def get_embeddings_model():
    """Centralized embeddings model initialization (Custom Torch Implementation)"""
    return CustomHuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )

def create_vector_db(chunks, course_id):
    """
    Creates and saves a FAISS vector index for a specific course.
    Path: media/vectorstore/course_<id>/
    """
    if not chunks:
        return
        
    from langchain_community.vectorstores import FAISS
    from django.conf import settings

    embeddings = get_embeddings_model()
    
    db = FAISS.from_documents(chunks, embeddings)
    
    # Store in media/vectorstore/course_<id>
    folder_path = os.path.join(settings.MEDIA_ROOT, 'vectorstore', f'course_{course_id}')
    os.makedirs(folder_path, exist_ok=True)
    
    db.save_local(folder_path)
    print(f"Vector DB saved for Course {course_id} at {folder_path}")

def load_vector_db(course_id):
    """
    Loads the FAISS vector index for a course.
    """
    from langchain_community.vectorstores import FAISS
    from django.conf import settings

    folder_path = os.path.join(settings.MEDIA_ROOT, 'vectorstore', f'course_{course_id}')
    if not os.path.exists(folder_path):
        return None
        
    embeddings = get_embeddings_model()
    
    try:
        return FAISS.load_local(folder_path, embeddings, allow_dangerous_deserialization=True)
    except Exception as e:
        print(f"Error loading Vector DB for Course {course_id}: {e}")
        return None
