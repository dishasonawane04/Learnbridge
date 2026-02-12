
import requests
import json
import time

url = "http://localhost:11434/api/generate"
payload = {
    "model": "llava:latest",
    "prompt": "Hello, are you working?",
    "stream": True,
    "options": {
        "temperature": 0.5
    }
}

print(f"Sending request to {url} with payload {payload}...")
start_time = time.time()

try:
    # Set a very long timeout for debugging
    response = requests.post(url, json=payload, stream=True, timeout=300)
    response.raise_for_status()
    
    print("Request sent. Waiting for first chunk...")
    
    first_chunk_received = False
    
    for line in response.iter_lines():
        if line:
            if not first_chunk_received:
                latency = time.time() - start_time
                print(f"SUCCESS: First chunk received after {latency:.2f} seconds.")
                first_chunk_received = True
            
            try:
                chunk = json.loads(line.decode('utf-8'))
                response_part = chunk.get('response', '')
                print(f"Chunk: {response_part}", end="", flush=True)
                if chunk.get('done'):
                    print("\nGeneration complete.")
                    break
            except json.JSONDecodeError:
                pass

    total_time = time.time() - start_time
    print(f"\nTotal time: {total_time:.2f} seconds")

except Exception as e:
    print(f"\nERROR: {e}")
    print(f"Time elapsed until error: {time.time() - start_time:.2f} seconds")
