import os, sys, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'learnbridge.settings')
django.setup()

from course.models import Course, CourseMaterial, CourseNotes

print("--- LATEST MATERIALS ---")
materials = CourseMaterial.objects.order_by('-id')[:3]
for m in materials:
    extr_len = len(m.extracted_text) if m.extracted_text else 0
    print(f"Material {m.id}: {m.file.name} | Type: {m.file_type} | Extracted chars: {extr_len}")
    if extr_len > 0 and extr_len < 300:
        print(f"  Content snippet: {m.extracted_text[:100]}")

print("\n--- LATEST NOTES ---")
notes = CourseNotes.objects.order_by('-updated_at')[:3]
for n in notes:
    extr_len = len(n.extracted_text) if n.extracted_text else 0
    print(f"Course {n.course.id} ({n.course.title}): Notes Extracted chars: {extr_len}")

