
import os
import django
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'learnbridge.settings')
django.setup()

from course.models import Course
from ai_core.retriever import search_course_material, cosine_similarity
from ai_core.embeddings import get_embedding
from ai_core.models import KnowledgeStore

def debug_retrieval():
    print("--- DEBUGGING RETRIEVAL ---")
    course = Course.objects.filter(title__icontains="Neural Network").first()
    if not course:
        print("Course not found.")
        return

    subject = "Neural Network"
    query_vector = get_embedding(subject)
    print(f"Query vector generated: {query_vector is not None}")
    if query_vector is None:
        print("ERROR: get_embedding failed for subject.")
        return
    
    chunks = KnowledgeStore.objects.filter(course=course)
    print(f"Chunks in DB for this course: {chunks.count()}")
    
    for i, chunk in enumerate(chunks):
        if chunk.embedding is None:
            print(f"Chunk {i+1} has NULL embedding!")
            continue
        sim = cosine_similarity(query_vector, chunk.embedding)
        print(f"Chunk {i+1} similarity: {sim:.4f}")
        print(f"Content snippet: {chunk.content[:100]}...")

    res = search_course_material(subject, course.id)
    print(f"Final search results: {len(res)}")

if __name__ == "__main__":
    debug_retrieval()
