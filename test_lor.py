import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'learnbridge.settings')
django.setup()
from django.contrib.auth.models import User
from django.test import RequestFactory
from django.contrib.messages.storage.fallback import FallbackStorage
from letter_of_recommendation_generator.views import letter_dashboard

factory = RequestFactory()
request = factory.get('/lor/')
request.user = User.objects.get(username='disha')
setattr(request, 'session', {})
messages = FallbackStorage(request)
setattr(request, '_messages', messages)

try:
    response = letter_dashboard(request)
    print('Status:', response.status_code)
    if response.status_code == 302:
        print('Redirected to:', response.url)
    else:
        print('Success!')
except Exception as e:
    print('Exception:', e)
