
import os
import django
import asyncio
import ollama

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'learnbridge.settings')
django.setup()

from django.conf import settings

async def check_ollama():
    print(f"Checking Ollama connection to {settings.OLLAMA_BASE_URL}...")
    try:
        # Try with library
        client = ollama.AsyncClient(host=settings.OLLAMA_BASE_URL)
        res = await client.list()
        print("Successfully connected to Ollama via library!")
        print(f"Available models: {[m['name'] for m in res['models']]}")
    except Exception as e:
        print(f"Library connection failed: {e}")
        
    try:
        # Try with raw requests
        import requests
        res = requests.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
        if res.status_code == 200:
            print("Successfully connected to Ollama via raw HTTP tags endpoint!")
        else:
            print(f"HTTP tags endpoint returned status {res.status_code}")
    except Exception as e:
        print(f"HTTP connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(check_ollama())
