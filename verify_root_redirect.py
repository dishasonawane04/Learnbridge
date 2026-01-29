import os
import sys
import django
from django.test import Client

# Setup Django environment
sys.path.append('d:\\DISHA\\learnbridge')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'learnbridge.settings')
django.setup()

def test_root_redirect():
    c = Client()
    print("Requesting '/' as Anonymous User...")
    response = c.get('/', HTTP_HOST='127.0.0.1:8000')
    
    print(f"Status Code: {response.status_code}")
    if response.status_code == 302:
        print(f"Redirect Location: {response.url}")
        if '/accounts/login/' in response.url:
            print("SUCCESS: Redirects to login page.")
        else:
            print("FAIL: Redirects to unexpected location.")
    elif response.status_code == 200:
        print("FAIL: Returned 200 OK (Dashboard accessible without login).")
    else:
        print(f"FAIL: Unexpected status {response.status_code}")

if __name__ == "__main__":
    test_root_redirect()
