import os
import django
import sys
sys.path.append('d:\\DISHA\\learnbridge')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'learnbridge.settings')
django.setup()

from letter_of_recommendation_generator.ai_logic import generate_recommendation_letter

data = {
    'student_name': 'Test',
    'course_degree': 'B.Tech',
    'institution_name': 'Uni',
    'duration_of_association': '1 year',
    'academic_performance': 'Good',
    'technical_skills': 'Python',
    'soft_skills': 'Good',
    'achievements': 'None',
    'purpose_display': 'Job',
    'tone_display': 'Neutral'
}

print("Invoking AI...")
res = generate_recommendation_letter(data)
print("RESULT:")
print(res)
