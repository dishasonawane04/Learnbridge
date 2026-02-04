import os
import django
import sys
from django.conf import settings
from django.test import RequestFactory

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'learnbridge.settings')
try:
    django.setup()
except Exception as e:
    print(f"Setup Error: {e}")
    sys.exit(1)

from learnbridge.views import dashboard
from django.contrib.auth.models import User

def test_dashboard_view():
    print("Testing dashboard view...")
    factory = RequestFactory()
    request = factory.get('/')
    
    # Try with an authenticated user
    try:
        # Get any user or create one
        user = User.objects.first()
        if not user:
            print("Creating temp user...")
            user = User.objects.create_user('debug_user', 'debug@example.com', 'password')
        
        print(f"Using user: {user.username}")
        request.user = user
        
        # Manually add session/messages if needed (view doesn't seem to use them directly but templates might)
        # But RequestFactory doesn't do middleware. 
        # dashboard view primarily checks request.user.
        
        response = dashboard(request)
        print(f"Response Status: {response.status_code}")
        if response.status_code != 200:
            print("Response Content (snippet):")
            print(response.content.decode('utf-8')[:1000])

    except Exception as e:
        print("\n!!! EXCEPTION CAUGHT !!!")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_dashboard_view()
