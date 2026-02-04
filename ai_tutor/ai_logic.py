from django.conf import settings
import time

# Placeholder for AI logic
# You might want to implement actual AI integration here using Ollama or other services as per settings.

def chat_with_ai(prompt, image_path=None, document_path=None, mode='text', stream=False):
    """
    Simulated AI response generator.
    Replace this with actual API calls to Ollama or other AI services.
    """
    
    # Simulating delay
    # time.sleep(1) 
    
    response_text = f"This is a simulated AI response for: {prompt[:50]}..."
    
    if image_path:
        response_text += " (Image analyzed)"
    if document_path:
        response_text += " (Document analyzed)"
        
    if stream:
        # Yield chunks for streaming
        msg = response_text
        chunk_size = 10
        for i in range(0, len(msg), chunk_size):
            yield msg[i:i+chunk_size]
            time.sleep(0.1)
    else:
        return response_text
