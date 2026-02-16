
import requests
import json

def test_ollama_embedding():
    url = "http://localhost:11434/api/embeddings"
    payload = {
        "model": "llama3.2:1b",
        "prompt": "Neural Network"
    }
    print(f"Testing URL: {url}")
    print(f"Payload: {json.dumps(payload)}")
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            embedding = data.get('embedding')
            if embedding:
                print(f"Success! Embedding size: {len(embedding)}")
                print(f"First 5 values: {embedding[:5]}")
            else:
                print("Response received but no embedding found.")
                print(f"Full response: {data}")
        else:
            print(f"Error: {response.text}")
            
        # Also test /api/embed (newer)
        url_new = "http://localhost:11434/api/embed"
        payload_new = {
            "model": "llama3.2:1b",
            "input": "Neural Network"
        }
        print(f"\nTesting NEW URL: {url_new}")
        response = requests.post(url_new, json=payload_new, timeout=30)
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
             data = response.json()
             embeddings = data.get('embeddings')
             if embeddings:
                 print(f"Success! Embedding size: {len(embeddings[0])}")
             else:
                 print("No embeddings found in /api/embed response.")
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    test_ollama_embedding()
