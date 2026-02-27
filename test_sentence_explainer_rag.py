import os
import django
import asyncio

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'learnbridge.settings')
django.setup()

from django.test import RequestFactory
from django.contrib.sessions.middleware import SessionMiddleware
from sentence_explain.views import sentence_explain
from asgiref.sync import sync_to_async
from django.contrib.auth.models import User

def setup_request(user, course_id=None):
    factory = RequestFactory()
    request = factory.get('/sentence-explain/')
    
    # Add session
    middleware = SessionMiddleware(lambda r: None)
    middleware.process_request(request)
    
    if course_id:
        request.session['active_course_id'] = str(course_id)
    
    request.user = user
    request.method = 'POST'
    request.POST = {'sentence': 'What is a neural network?'}
    return request

async def test_explainer():
    print("Verifying SynchronousOnlyOperation fix...")
    
    # Use a real user
    user = await sync_to_async(User.objects.first)()
    if not user:
        print("No user found in DB, search for any user.")
        return

    # Test with Course 4
    print("\n--- Testing Course 4 ---")
    request = setup_request(user, 4)
    request.session['chat_history'] = []
    
    try:
        response = await sentence_explain(request)
        print(f"Success! Status: {response.status_code}")
        history = request.session.get('chat_history', [])
        if history:
            print(f"AI Response: {history[-1]['content'][:200]}...")
    except Exception as e:
        print(f"Failed with error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_explainer())
