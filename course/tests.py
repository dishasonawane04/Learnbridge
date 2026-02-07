from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User
from django.urls import reverse
from .models import Course, CourseUnit, CourseMaterial
from .views import course_create, unit_add, material_upload, unit_ai_chat
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.messages.middleware import MessageMiddleware
from django.core.files.uploadedfile import SimpleUploadedFile
import json

class CourseFunctionalTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(username='teststudent', password='password123')

    def add_middleware(self, request):
        """Annotate a request object with a session and messages"""
        middleware = SessionMiddleware(lambda x: x)
        middleware.process_request(request)
        request.session.save()
        
        middleware = MessageMiddleware(lambda x: x)
        middleware.process_request(request)

    def test_course_creation_flow(self):
        """
        Verify view logic directly using RequestFactory to avoid Client template issues.
        """
        # 1. Create Course
        request = self.factory.post(reverse('course:create'), {
            'title': 'Intro to Python',
            'description': 'A basic python course',
            'level': 'UG'
        })
        request.user = self.user
        self.add_middleware(request)
        
        response = course_create(request)
        self.assertEqual(response.status_code, 302)
        
        course = Course.objects.first()
        self.assertIsNotNone(course)
        self.assertEqual(course.title, 'Intro to Python')
        
        # 2. Add Unit
        request = self.factory.post(reverse('course:unit_add', args=[course.id]), {
            'title': 'Unit 1: Variables',
            'order': 1
        })
        request.user = self.user
        self.add_middleware(request)
        
        response = unit_add(request, course.id)
        self.assertEqual(response.status_code, 302)
        
        unit = CourseUnit.objects.first()
        self.assertIsNotNone(unit)
        self.assertEqual(unit.title, 'Unit 1: Variables')

        # 3. Upload Material
        file_content = b"Python variables are containers for storing data values."
        uploaded_file = SimpleUploadedFile("python_vars.txt", file_content, content_type="text/plain")
        
        request = self.factory.post(reverse('course:material_upload', args=[unit.id]), {
            'file': uploaded_file
        })
        request.user = self.user
        self.add_middleware(request)
        
        response = material_upload(request, unit.id)
        self.assertEqual(response.status_code, 302)
        
        # Verify extraction
        material = CourseMaterial.objects.first()
        self.assertIsNotNone(material)
        self.assertEqual(material.extracted_text, "Python variables are containers for storing data values.")

    def test_ai_assistant_integration(self):
        """
        Verify the AI chat endpoint works and context is injected.
        """
        # Setup data
        course = Course.objects.create(user=self.user, title='AI 101', level='UG')
        unit = CourseUnit.objects.create(course=course, title='Neural Networks', content="NNs are inspired by the brain.")
        
        # Send Chat Message
        payload = {'message': 'What are neural networks?'}
        request = self.factory.post(
            reverse('course:unit_ai_chat', args=[unit.id]),
            data=json.dumps(payload),
            content_type='application/json'
        )
        request.user = self.user
        self.add_middleware(request)
        
        response = unit_ai_chat(request, unit.id)
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn('response', data)
        self.assertIn('Academic Response', data['response'])
        self.assertIn('Neural Networks', data['response'])

