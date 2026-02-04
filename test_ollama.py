import ollama
try:
    print("Testing Ollama connection...")
    models = ollama.list()
    print("Models available:", [m['name'] for m in models['models']])
    
    print("Testing chat with llama3...")
    response = ollama.chat(model='llama3', messages=[{'role': 'user', 'content': 'hello'}])
    print("Response:", response['message']['content'])
except Exception as e:
    print("Error:", e)
