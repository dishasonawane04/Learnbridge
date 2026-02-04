import os
import django
import sys

# Setup Django environment
sys.path.append('d:\\DISHA\\learnbridge')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'learnbridge.settings')
django.setup()

from letter_of_recommendation_generator.models import LetterRequest
from letter_of_recommendation_generator.ai_logic import generate_recommendation_letter
from django.test import RequestFactory
from letter_of_recommendation_generator.views import download_letter_pdf, download_letter_docx

def test_generation():
    print("Testing AI Generation...")
    data = {
        'student_name': 'Test Student',
        'course_degree': 'B.Tech',
        'institution_name': 'Test Uni',
        'duration_of_association': '4 years',
        'academic_performance': 'Excellent',
        'technical_skills': 'Python',
        'soft_skills': 'Good leader',
        'achievements': 'Won hackathon',
        'purpose_display': 'Job',
        'tone_display': 'Strong'
    }
    
    # Mock AI response if needed, but let's try real first
    try:
        letter = generate_recommendation_letter(data)
        print(f"Generated Letter Length: {len(letter)}")
        if "Error" in letter:
            print("AI Generation FAILED with error message.")
        else:
            print("AI Generation SUCCESS.")
        return letter
    except Exception as e:
        print(f"AI Generation CRASHED: {e}")
        return None

def test_downloads(letter_content):
    print("\nTesting Download Views...")
    # Create a dummy request
    obj = LetterRequest.objects.create(
        student_name="Test Student",
        generated_letter=letter_content or "Dummy content"
    )
    
    factory = RequestFactory()
    request = factory.get(f'/lor/download/pdf/{obj.pk}/')
    
    # Test PDF
    try:
        resp_pdf = download_letter_pdf(request, obj.pk)
        print(f"PDF Status: {resp_pdf.status_code}")
        print(f"PDF Content-Type: {resp_pdf['Content-Type']}")
        if resp_pdf.status_code == 200 and 'application/pdf' in resp_pdf['Content-Type']:
            print("PDF Download SUCCESS")
        else:
            print("PDF Download FAILED")
    except Exception as e:
        print(f"PDF Download CRASHED: {e}")

    # Test DOCX
    try:
        resp_docx = download_letter_docx(request, obj.pk)
        print(f"DOCX Status: {resp_docx.status_code}")
        print(f"DOCX Content-Type: {resp_docx['Content-Type']}")
        if resp_docx.status_code == 200 and 'wordprocessingml' in resp_docx['Content-Type']:
            print("DOCX Download SUCCESS")
        else:
            print("DOCX Download FAILED")
    except Exception as e:
        print(f"DOCX Download CRASHED: {e}")

if __name__ == "__main__":
    content = test_generation()
    test_downloads(content)
