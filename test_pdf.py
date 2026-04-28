import os
import django
from django.conf import settings
from django.template.loader import get_template
from xhtml2pdf import pisa
from io import BytesIO

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'learnbridge.settings')
django.setup()

def test_pdf_generation():
    template_src = 'analytics/reports/student_report_pdf.html'
    context = {
        'display_name': 'Test Student',
        'target_user': type('obj', (object,), {'email': 'test@example.com', 'username': 'testuser'}),
        'now': django.utils.timezone.now(),
        'avg_score': 85.5,
        'high_score': 95,
        'latest_score': 88,
        'trend': 'Improving',
        'ai_interactions': 15,
        'flashcards_count': 10,
        'weak_topics': [('Math', 5), ('Science', 3)],
        'attempts': [],
        'ai_insights': ['Great progress.'],
        'recommendations': ['Keep it up.'],
    }
    
    template = get_template(template_src)
    html = template.render(context)
    result = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(html.encode("UTF-8")), result)
    
    if not pdf.err:
        with open('test_report.pdf', 'wb') as f:
            f.write(result.getvalue())
        print("PDF generated successfully.")
        print(f"File size: {os.path.getsize('test_report.pdf')} bytes")
    else:
        print("PDF generation failed.")

if __name__ == "__main__":
    test_pdf_generation()
