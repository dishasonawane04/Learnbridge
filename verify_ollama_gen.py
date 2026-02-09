import requests
import json
import sys

def verify_ollama():
    base_url = "http://127.0.0.1:11434"
    
    # 1. Check Tags (Health)
    print(f"Checking status at {base_url}/api/tags...")
    try:
        response = requests.get(f"{base_url}/api/tags", timeout=5)
        if response.status_code == 200:
            print("SUCCESS: Ollama server is running and reachable.")
        else:
            print(f"WARNING: Server reachable but returned {response.status_code}")
    except requests.exceptions.ConnectionError:
        print("FAILURE: Could not connect to Ollama. Service is NOT running.")
        return False
    except Exception as e:
        print(f"FAILURE: Error checking status: {e}")
        return False

    # 2. Check Generation
    url = f"{base_url}/api/generate"
    payload = {
        "model": "llama3.2:1b",
        "prompt": "Hello",
        "stream": False
    }
    
    print(f"Testing basic generation with 'llama3.2:1b' (Timeout: 60s)...")
    try:
        response = requests.post(url, json=payload, timeout=60)
        if response.status_code == 200:
            data = response.json()
            print("SUCCESS: Model generated response!")
            print(f"Response: {data.get('response', '')}")
            return True
        else:
            print(f"FAILURE: Generation failed. Status: {response.status_code}")
            print(response.text)
            return False
    except requests.exceptions.ReadTimeout:
        print("FAILURE: Request timed out (60s). Model might be stuck loading.")
        return False
    except Exception as e:
        print(f"FAILURE: Generation error: {e}")
        return False

if __name__ == "__main__":
    success = verify_ollama()
    if not success:
        sys.exit(1)
