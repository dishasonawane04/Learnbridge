import re
from .models import KnowledgeStore
from .embeddings import get_embedding
from course.models import Course

def clean_text(text):
    """Basic text cleaning."""
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def chunk_text(text, word_limit=500):
    """Splits text into chunks of roughly word_limit words."""
    words = text.split()
    chunks = []
    for i in range(0, len(words), word_limit):
        chunk = " ".join(words[i:i + word_limit])
        chunks.append(chunk)
    return chunks

def process_course_notes_into_knowledge_store(course_id, extracted_content):
    """
    Chunks the extracted content (paged or string), generates embeddings, and saves to KnowledgeStore with metadata.
    """
    try:
        course = Course.objects.get(id=course_id)
        
        # extracted_content can be a list of dicts (pages) or a single string
        pages = []
        if isinstance(extracted_content, list):
            pages = extracted_content
        else:
            pages = [{'page_number': 1, 'text': extracted_content}]

        new_chunks = []
        for page_data in pages:
            page_num = page_data.get('page_number', 1)
            text = clean_text(page_data.get('text', ''))
            
            # User asked for 400-600 words. Let's stick to ~500.
            chunks = chunk_text(text, word_limit=500)
            
            for i, chunk in enumerate(chunks):
                if len(chunk.strip()) < 50: continue # Skip tiny fragments
                
                # Check for existing to avoid exact duplicates
                if KnowledgeStore.objects.filter(course=course, content=chunk).exists():
                    continue

                vector = get_embedding(chunk)
                if vector:
                    new_chunks.append(
                        KnowledgeStore(
                            course=course,
                            content=chunk,
                            embedding=vector,
                            metadata={
                                'page_number': page_num,
                                'chunk_index': i
                            }
                        )
                    )
        
        if new_chunks:
            KnowledgeStore.objects.bulk_create(new_chunks)
            return True
        return False
    except Exception as e:
        print(f"Error processing knowledge store: {e}")
        return False
