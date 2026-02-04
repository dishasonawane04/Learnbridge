import ollama
import os
from django.conf import settings

# Load System Prompt
PROMPT_PATH = os.path.join(settings.BASE_DIR, 'learning_support', 'prompts', 'support_system_prompt.txt')

try:
    with open(PROMPT_PATH, 'r', encoding='utf-8') as f:
        SUPPORT_SYSTEM_PROMPT = f.read()
except Exception as e:
    SUPPORT_SYSTEM_PROMPT = "You are a helpful Learning Support Assistant."
    print(f"Error loading prompt: {e}")

def get_support_response(user_message, mode='text', stream=False):
    """
    Generates a response from Ollama using the Support Persona.
    Supports streaming.
    """
    try:
        messages = [
            {'role': 'system', 'content': SUPPORT_SYSTEM_PROMPT},
            {'role': 'user', 'content': user_message}
        ]

        # Append specific instruction for Voice Mode if active
        if mode == 'voice':
             messages[0]['content'] += "\n\nCURRENT MODE: VOICE. Respond conversationally and include a '🎙️ Spoken Explanation' section."

        response = ollama.chat(
            model="llama3", 
            messages=messages,
            stream=stream
        )

        if stream:
            return (chunk['message']['content'] for chunk in response)
        
        return response['message']['content']

    except Exception as e:
        error_msg = f"Support AI Error: {str(e)}"
        if stream:
            return (x for x in [error_msg])
        return error_msg
