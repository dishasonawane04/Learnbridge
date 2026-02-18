from django.core.management.base import BaseCommand
from course.models import Course, CourseMaterial
from ai_engine.course_processor import process_document
import os

class Command(BaseCommand):
    help = 'Process course documents using RAG pipeline for existing files'

    def add_arguments(self, parser):
        parser.add_argument('course_id', type=int, help='Course ID to process')

    def handle(self, *args, **options):
        course_id = options['course_id']
        self.stdout.write(f"Processing Course {course_id}...")
        
        try:
            course = Course.objects.get(id=course_id)
        except Course.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"Course {course_id} not found"))
            return

        materials = CourseMaterial.objects.filter(course=course)
        
        processed_count = 0
        
        # Process main file
        if course.uploaded_file and os.path.exists(course.uploaded_file.path):
             self.stdout.write(f"Processing Main File: {course.uploaded_file.path}")
             if process_document(course.uploaded_file.path, course_id):
                 processed_count += 1
        
        # Process materials
        for mat in materials:
            if mat.file and os.path.exists(mat.file.path):
                self.stdout.write(f"Processing Material: {mat.file.path}")
                if process_document(mat.file.path, course_id):
                    processed_count += 1
                    
        self.stdout.write(self.style.SUCCESS(f"Successfully processed {processed_count} documents for Course {course_id}"))
