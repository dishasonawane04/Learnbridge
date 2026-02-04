import requests
import json

def check_ollama():
    url = "http://localhost:11434/api/tags"
    try:
        print(f"Attempting to connect to {url}...")
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            print("Connection Successful!")
            models = response.json().get('models', [])
            print("Available Models:")
            for m in models:
                print(f" - {m.get('name')}")
        else:
            print(f"Connected, but returned status code: {response.status_code}")
    except requests.exceptions.ConnectionError:
        print("Connection Failed: Could not connect to localhost:11434. Is Ollama running?")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    check_ollama()
