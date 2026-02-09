import requests
import json

def test_chat_api():
    url = "http://127.0.0.1:8000/ai/api/chat/"
    
    # Simulate FormData used in script.js
    data = {
        "message": "Hello from debug script",
        "type": "text",
        # chat_id optional
    }
    
    # We assume 'csrftoken' cookie is not strictly needed due to @csrf_exempt, 
    # but let's see. script.js sends X-CSRFToken. 
    # Since view is @csrf_exempt, we can skip it.
    
    print(f"Sending POST to {url}...")
    try:
        # Note: script.js sends FormData, which requests handles if we pass 'data='
        response = requests.post(url, data=data, stream=True, timeout=120)
        
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            print("Response Headers:", response.headers)
            print("Streaming content...")
            content_received = ""
            for chunk in response.iter_content(chunk_size=None):
                if chunk:
                    decoded = chunk.decode('utf-8')
                    content_received += decoded
                    print(decoded, end='', flush=True)
            print("\n\nFull response received.")
            if "AI Error" in content_received:
                print("FAILURE: Backend returned AI Error.")
            else:
                print("SUCCESS: Full response ok.")
        else:
            print("FAILURE: Non-200 Status.")
            print(response.text)

    except Exception as e:
        print(f"FAILURE: Request failed: {e}")

if __name__ == "__main__":
    test_chat_api()
