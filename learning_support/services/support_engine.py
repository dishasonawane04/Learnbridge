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

def get_support_response(user_message, mode='text', stream=False, context=None, custom_system_prompt=None):
    """
    Generates a response from Ollama using the Support Persona with RAG context.
    """
    try:
        from core.middleware import get_current_request
        request = get_current_request()
        lang = "English"
        if request:
            if request.method == "POST":
                lang = request.POST.get("language", "English")
            elif hasattr(request, 'session'):
                lang = request.session.get('ai_language', 'English')

        current_system_prompt = custom_system_prompt if custom_system_prompt else SUPPORT_SYSTEM_PROMPT
        
        # If context exists and not using a custom prompt that already includes it
        if context and not custom_system_prompt:
            current_system_prompt += f"\n\nCONTEXT:\n{context}"
            
        if lang.lower() != "english":
             current_system_prompt += f"\n\nIMPORTANT: Please explain in {lang}. Ensure the response is strictly in {lang}."

        final_prompt = f"{current_system_prompt}\n\nQUESTION: {user_message}"
        if mode == 'voice':
             final_prompt += "\n\nCURRENT MODE: VOICE. Respond conversationally and include a '🎙️ Spoken Explanation' section."

        messages = [
            {'role': 'user', 'content': final_prompt}
        ]

        response = ollama.chat(
            model="tinyllama:latest", # Switch to faster model
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
