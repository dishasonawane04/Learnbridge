
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'learnbridge.settings')
django.setup()

from ai_core.retriever import search_course_material
from course.models import Course

def dump_chunks():
    course = Course.objects.filter(title__icontains="Neural Network").first()
    if not course:
        print("Course not found")
        return
        
    chunks = search_course_material("Neural Network", course.id)
    with open('chunks_debug.txt', 'w', encoding='utf-8') as f:
        for i, chunk in enumerate(chunks):
            f.write(f"--- CHUNK {i} ---\n")
            f.write(chunk)
            f.write("\n\n")
    print(f"Dumped {len(chunks)} chunks to chunks_debug.txt")

if __name__ == "__main__":
    dump_chunks()
