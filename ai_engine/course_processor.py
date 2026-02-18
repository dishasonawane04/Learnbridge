from ai_engine.document_loader import load_document
from ai_engine.chunker import split_into_chunks
from ai_engine.vector_store import create_vector_db, load_vector_db, get_embeddings_model
import os

def process_document(file_path, course_id):
    """
    Process a single document and add it to the course vector store.
    """
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return False
        
    print(f"Processing for Course {course_id}: {file_path}")
    
    # 1. Load
    pages = load_document(file_path)
    if not pages:
        print("No content loaded.")
        return False
        
    # 2. Split
    chunks = split_into_chunks(pages)
    print(f"Generated {len(chunks)} chunks.")
    
    # 3. Embed & Store
    existing_db = load_vector_db(course_id)
    
    if existing_db:
        print(f"Updating existing Vector DB for Course {course_id}")
        new_db = create_vector_db_instance(chunks)
        existing_db.merge_from(new_db)
        save_vector_db(existing_db, course_id)
    else:
        print(f"Creating new Vector DB for Course {course_id}")
        create_vector_db(chunks, course_id)

    # 4. Sync to KnowledgeStore (DB) for UI consistency
    try:
        from ai_core.services import process_course_notes_into_knowledge_store
        # Convert langchain documents back to a format process_course_notes understands or simulate it
        # Actually, simpler to just pass the content since it handles merging
        full_text = "\n\n".join([c.page_content for c in chunks])
        process_course_notes_into_knowledge_store(course_id, full_text)
    except Exception as e:
        print(f"DB Sync Error: {e}")
    
    return True

def create_vector_db_instance(chunks):
    """Helper to create a local FAISS instance in memory"""
    from langchain_community.vectorstores import FAISS
    embeddings = get_embeddings_model()
    return FAISS.from_documents(chunks, embeddings)

def save_vector_db(db, course_id):
    """Helper to save the DB"""
    from django.conf import settings
    folder_path = os.path.join(settings.MEDIA_ROOT, 'vectorstore', f'course_{course_id}')
    os.makedirs(folder_path, exist_ok=True)
    db.save_local(folder_path)
