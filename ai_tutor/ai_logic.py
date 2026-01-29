import ollama
import os
from PIL import Image
from io import BytesIO
import pypdf
import docx

SYSTEM_PROMPT = (
    "You are Learning Support AI, a student-focused assistant in LearnBridge.\n"
    "PURPOSE: Help students move from confusion to clarity using hints and simplified guidelines.\n\n"
    "USER INSTRUCTION PRIORITY RULE:\n"
    "Always strictly follow the user's latest instructions (e.g. 'Short answer', 'No emojis').\n"
    "This overrides default formatting.\n\n"
    "SUPPORT STRATEGY:\n"
    "1. IDENTIFY: Understand the struggle. Ask 1 clarifying question if needed.\n"
    "2. SIMPLIFY: Re-explain using simple language and short sentences.\n"
    "3. ALTERNATE: Provide a real-life or relatable example.\n"
    "4. HINT: Do NOT give the final answer immediately. Provide step-by-step hints.\n\n"
    "RESPONSE STRUCTURE (Default):\n"
    "🧠 **Simplified Explanation**\n"
    "Clear, easy-to-understand explanation.\n\n"
    "🔁 **Alternate Example**\n"
    "Relatable scenario.\n\n"
    "🧩 **Guided Hints**\n"
    "Hint 1: Directional\n"
    "Hint 2: Structural\n"
    "Hint 3: Near-solution (only if needed)\n\n"
    "❓ **Check for Understanding**\n"
    "One short question."
)

VOICE_SYSTEM_PROMPT = (
    "You are Learning Support AI, operating in FULL DUPLEX VOICE MODE.\n"
    "Your goal is a natural, hands-free conversation. You MUST speak back.\n\n"
    "USER INSTRUCTION PRIORITY RULE:\n"
    "Always strictly follow the user's latest instructions (e.g. 'No emojis').\n\n"
    "VOICE SUPPORT PRINCIPLES:\n"
    "1. PATIENCE: Be calm and encouraging. Never judge.\n"
    "2. GUIDE: Don't just answer; guide them with hints.\n"
    "3. ADAPT: If struggling, simplify. If doing well, ask harder questions.\n\n"
    "RESPONSE STRUCTURE (Strictly Follow):\n"
    "📘 **Concept / Topic**\n\n"
    "🧠 **Simplified Text Explanation:**\n"
    "Easy to read summary.\n\n"
    "🎙️ **Spoken Explanation:**\n"
    "Conversational, supportive explanation with hints. MANDATORY.\n\n"
    "🧩 **Guided Hints (Spoken)**:\n"
    "Weave hints into the spoken part if they are stuck.\n\n"
    "❓ **Spoken Follow-up:**\n"
    "Check for understanding verbally.\n\n"
    "🎧 **(Wait for response)**"
)

def resize_image(image_path, max_size=1024):
    """Resizes an image to a maximum dimension while maintaining aspect ratio."""
    try:
        with Image.open(image_path) as img:
            ratio = min(max_size / img.width, max_size / img.height)
            if ratio < 1:
                new_size = (int(img.width * ratio), int(img.height * ratio))
                img = img.resize(new_size, Image.Resampling.LANCZOS)
                img.save(image_path)
                return True
    except Exception as e:
        print(f"Image resize error: {e}")
    return False

def extract_text_from_file(file_path):
    """Extracts text from PDF, DOCX, or TXT files."""
    ext = os.path.splitext(file_path)[1].lower()
    text = ""
    
    try:
        if ext == '.pdf':
            reader = pypdf.PdfReader(file_path)
            for page in reader.pages:
                text += page.extract_text() + "\n"
        elif ext == '.docx':
            doc = docx.Document(file_path)
            text = "\n".join([p.text for p in doc.paragraphs])
        elif ext == '.txt':
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
    except Exception as e:
        return f"[Error extraction text: {str(e)}]"
        
    return text[:6000] # Limit tokens

def chat_with_ai(prompt, image_path=None, document_path=None, mode='text', stream=False):
    """
    Communicates with Ollama. 
    If stream=True, returns a generator yielding text chunks.
    Otherwise, returns the full string response.
    """
    try:
        # Optimization: Resize Image if present
        if image_path:
            resize_image(image_path)

        # Select System Prompt based on Mode
        sys_prompt = VOICE_SYSTEM_PROMPT if mode == 'voice' else SYSTEM_PROMPT
        
        messages = [{'role': 'system', 'content': sys_prompt}]
        
        # 1. Image Analysis (Use Llava) - Llava usually doesn't stream well or context might differ, 
        # but let's assume we want text output streamed.
        if image_path:
            user_msg = {
                'role': 'user',
                'content': prompt if prompt else "Explain this image in detail.",
                'images': [image_path]
            }
            # Note: Streaming with images in ollama-python might vary, assuming standard behavior
            response = ollama.chat(
                model="llava",
                messages=[messages[0], user_msg],
                stream=stream
            )
            if stream:
                return (chunk['message']['content'] for chunk in response)
            return response['message']['content']

        # 2. Document Analysis (Text Extraction + Llama3)
        if document_path:
            extracted_text = extract_text_from_file(document_path)
            context_prompt = (
                f"Analyze this document content:\n\n{extracted_text}\n\n"
                f"User Instruction: {prompt if prompt else 'Explain this document.'}"
            )
            messages.append({'role': 'user', 'content': context_prompt})
            
            response = ollama.chat(
                model="llama3",
                messages=messages,
                stream=stream
            )
            if stream:
                return (chunk['message']['content'] for chunk in response)
            return response['message']['content']

        # 3. Text Only
        messages.append({'role': 'user', 'content': prompt})
        response = ollama.chat(
            model="llama3",
            messages=messages,
            stream=stream
        )
        if stream:
            return (chunk['message']['content'] for chunk in response)
        return response['message']['content']

    except Exception as e:
        err_msg = f"AI Error: {str(e)}. (Ensure models are pulled)"
        if stream:
            return (x for x in [err_msg]) # fallback generator
        return err_msg
