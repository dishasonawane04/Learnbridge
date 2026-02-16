import ollama
import json
import os
import re
import pypdf
import docx

SYSTEM_PROMPT = (
    "You are an AI-powered Flashcard Generator.\n"
    "Your task is to generate exam-ready flashcards based on the provided text.\n\n"
    "📌 Core Rules (STRICT)\n"
    "- Generate 8–12 flashcards\n"
    "- Each flashcard must include: One Question, One Answer, One Exam Tip\n"
    "- Content must be accurate and derived from the input\n\n"
    "📄 Output Format (STRICT – DO NOT CHANGE)\n"
    "Q: <question>\n"
    "A: <answer>\n"
    "ExamTip: <one-line exam-focused tip>\n"
    "Confidence: Unrated\n\n"
    "Q: <question>\n"
    "A: <answer>\n"
    "ExamTip: <tip>\n"
    "Confidence: Unrated\n\n"
    "(Leave exactly one blank line between flashcards)\n\n"
    "🎯 Feature 5: Exam Tip Rule\n"
    "- ExamTip must be: One single line, Helpful for revision, Not an explanation (e.g., 'Frequently asked as a definition')\n\n"
    "🎯 Feature 7: Flashcards → Quiz Conversion\n"
    "If the user requests quiz generation, convert each card into an MCQ (4 options). Provide answers at the end.\n\n"
    "🔍 QA Context Check: Ensure questions are stand-alone and clear."
)

DELETE_PROMPT = (
    "If the user requests to delete a flashcard, follow these rules:\n"
    "The user may specify: A question text, A keyword, Or a flashcard index.\n"
    "Deletion Rules:\n"
    "- Identify the matching flashcard accurately\n"
    "- Remove only that flashcard\n"
    "- Do NOT regenerate or modify other flashcards\n"
    "- Do NOT reorder remaining flashcards\n"
    "After Deletion, Respond with:\n"
    "- A short confirmation message (1 line)\n"
    "- The updated flashcard list in the same strict format: Q: ... A: ...\n"
    "If No Match Is Found:\n"
    "- Respond with a single line: 'Flashcard not found. Please specify the question or keyword.'"
)

def extract_text(file_path):
    ext = os.path.splitext(file_path)[1].lower()
    text = ""
    try:
        if ext == '.pdf':
            reader = pypdf.PdfReader(file_path)
            for page in reader.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n"
        elif ext == '.docx':
            doc = docx.Document(file_path)
            text = "\n".join([p.text for p in doc.paragraphs])
        elif ext == '.txt':
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
    except Exception as e:
        print(f"Error extracting text from {file_path}: {e}")
        return ""
    return text[:15000] # Limit content to avoid context window overflow

def parse_qa_text(response_text):
    """
    Parses Q: ... A: ... ExamTip: ... format into list of dicts.
    """
    cards = []
    # Regex to find blocks. 
    # Q: ... A: ... ExamTip: ... (Confidence optional)
    # We use non-greedy matching .*?
    
    # Try pattern with Confidence first
    pattern_full = r"Q:\s*(.*?)\s*\nA:\s*(.*?)\s*\nExamTip:\s*(.*?)\s*\nConfidence:\s*(.*?)(?=\nQ:|$)"
    matches = re.findall(pattern_full, response_text, re.DOTALL)
    
    if not matches:
        # Try pattern without Confidence (since model might skip it)
        pattern_tip = r"Q:\s*(.*?)\s*\nA:\s*(.*?)\s*\nExamTip:\s*(.*?)(?=\nQ:|\nConfidence:|$)"
        matches_tip = re.findall(pattern_tip, response_text, re.DOTALL)
        for q, a, tip in matches_tip:
             matches.append((q, a, tip, ""))

    for q, a, tip, conf in matches:
        q = q.strip()
        a = a.strip()
        tip = tip.strip()
        if q and a:
            cards.append({
                "front": q,
                "back": a,
                "exam_tip": tip,
                "type": "QA",
                "difficulty": "Hard" 
            })
            
    # Fallback for old/simple format (Q: A:) if regex misses
    if not cards:
         pattern_simple = r"Q:\s*(.*?)\s*\nA:\s*(.*?)(?=\nQ:|$)"
         matches_simple = re.findall(pattern_simple, response_text, re.DOTALL)
         for q, a in matches_simple:
             # Check if we already have this (partial match issue)
             # But if pattern matched above, we wouldn't be here.
             # So this handles "A: ... \n\n Q:" only cases.
             # We need to exclude if it has ExamTip inside A.
             if "ExamTip:" not in a:
                 cards.append({
                    "front": q.strip(),
                    "back": a.strip(),
                    "exam_tip": "",
                    "type": "QA",
                    "difficulty": "Hard"
                 })
            
    return cards

def clean_json_response(response_text):
    """
    ATTEMPT 1: Try Text Parsing (Q: A: format)
    ATTEMPT 2: Try JSON Parsing (Fallback for legacy/other models)
    """
    # 1. Try strict Q/A Text Parsing first (since Prompt requests it)
    cards = parse_qa_text(response_text)
    if cards and len(cards) > 0:
        return cards

    # 2. Fallback to JSON logic
    if isinstance(response_text, dict): 
        return response_text.get('cards', response_text.get('flashcards', []))

    text = response_text.strip()
    
    # Remove Markdown code blocks if present
    text = re.sub(r'^```json\s*', '', text, flags=re.MULTILINE)
    text = re.sub(r'^```\s*', '', text, flags=re.MULTILINE)
    text = re.sub(r'\s*```$', '', text, flags=re.MULTILINE)
    
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
        
    try:
        pattern = r"\[\s*\{.*\}\s*\]"
        match = re.search(pattern, text, re.DOTALL)
        if match:
             return json.loads(match.group())
    except Exception:
        pass

    try:
        pattern = r"\{.*\}"
        match = re.search(pattern, text, re.DOTALL)
        if match:
            data = json.loads(match.group())
            for key in ['cards', 'flashcards', 'response', 'data']:
                if key in data and isinstance(data[key], list):
                    return data[key]
    except Exception:
        pass
         
    return []

def generate_flashcards(input_text=None, file_path=None, difficulty="Medium", course_id=None):
    """
    Generates flashcards using Course-Aware RAG.
    """
    content = input_text if input_text else ""
    
    # 1. RAG Context Retrieval if course_id provided
    if course_id:
        from ai_core.retriever import search_course_material
        # Search using input_text as query if provided, otherwise general search
        query = input_text if input_text else "key concepts and definitions"
        relevant_chunks = search_course_material(query, course_id, top_k=5)
        if relevant_chunks:
            content = "\n".join(relevant_chunks) + "\n" + content

    # 2. Extract Text from File (if any)
    if file_path:
        # ... existing file extraction logic ...
        ext = os.path.splitext(file_path)[1].lower()
        if ext in ['.png', '.jpg', '.jpeg', '.webp']:
             try:
                 user_msg = {'role': 'user', 'content': 'Extract all text and key concepts from this image details.', 'images': [file_path]}
                 desc_response = ollama.chat(model="llava", messages=[user_msg])
                 content += "\nImage Content:\n" + desc_response['message']['content']
             except Exception as e:
                 print(f"Vision model error: {e}")
                 if not content.strip(): return []
        else:
             file_text = extract_text(file_path)
             if file_text: content += "\n" + file_text

    if len(content.strip()) < 10:
        return []

    system_prompt = (
        f"{SYSTEM_PROMPT}\n\n"
        "STRICT RULE: Only use the provided course material to generate cards. "
        "Focus on definitions, formulas, and important points."
    )

    prompt = f"📥 Input Content:\n{content}\n"

    messages = [
        {'role': 'system', 'content': system_prompt},
        {'role': 'user', 'content': prompt}
    ]

    # Model priority: Prefer tinyllama for stability/speed on CPU
    models_to_try = ["tinyllama:latest", "llama3.2:1b", "mistral"]
    response = None
    used_model = None

    for model in models_to_try:
        try:
            print(f"Attempting flashcard generation with model: {model}")
            # Try without format='json' because our prompt specifically asks for text format Q: A:
            response = ollama.chat(model=model, messages=messages)
            used_model = model
            break 
        except Exception as e:
            error_str = str(e).lower()
            if "not found" in error_str or "pull" in error_str:
                 print(f"Model {model} not found, trying next...")
                 continue
            else:
                 # If it's a different error (e.g. context too long), try next or fail
                 print(f"Model {model} failed with error: {e}")
                 continue

    if not response:
        print("All AI models failed to respond.")
        return []

    ai_output = response['message']['content'].strip()
    
    # Logging for debug
    print(f"AI Output ({used_model}): {ai_output}...")

    cards = clean_json_response(ai_output)
    
    # Handle single object response
    if isinstance(cards, dict):
        if 'front' in cards and 'back' in cards:
            cards = [cards]
        else:
            cards = []

    # Final Validation
    valid_cards = []
    if isinstance(cards, list):
        for c in cards:
            if isinstance(c, dict) and 'front' in c and 'back' in c:
                valid_cards.append(c)
    
    return valid_cards

def explain_card_content(card_front, card_back):
    """
    Generates a simpler explanation for a specific card.
    """
    try:
        prompt = (
            f"Term/Question: {card_front}\n"
            f"Answer: {card_back}\n\n"
            "I am finding this card difficult. Please provide:\n"
            "1. A simpler explanation.\n"
            "2. A new, relatable example.\n"
            "3. A pneumonic or hint if possible.\n\n"
            "Keep it short and conversational."
        )
        
        messages = [{'role': 'user', 'content': prompt}]
        
        # Try a quick model
        try:
            response = ollama.chat(model="llama3.2", messages=messages)
        except:
            response = ollama.chat(model="llama3", messages=messages)

        return response['message']['content']
    except Exception as e:
        return f"Error: Could not generate explanation ({str(e)}). Please ensure Ollama is running."

def generate_quiz_from_cards(cards_list):
    """
    Converts a list of flashcards (dicts) into an MCQ quiz content.
    """
    if not cards_list:
        return []

    # Format content for AI
    content = ""
    for i, card in enumerate(cards_list):
        content += f"Q: {card.get('front')}\nA: {card.get('back')}\n\n"

    # STRICT format instructions are key here
    prompt = (
        "You are an expert Quiz Generator. Your task is to convert flashcards into a Multiple Choice Quiz (MCQ).\n\n"
        "STRICT Output Requirements:\n"
        "1. Output MUST be a valid JSON Array.\n"
        "2. No markdown formatting (no ```json or ```).\n"
        "3. Each valid JSON object must have keys: 'question', 'options' (array of 4 strings), 'answer' (single letter string).\n\n"
        "Example Output:\n"
        "[\n"
        "  {\n"
        "    \"question\": \"What is the capital of France?\",\n"
        "    \"options\": [\"A. Berlin\", \"B. Madrid\", \"C. Paris\", \"D. Rome\"],\n"
        "    \"answer\": \"C\"\n"
        "  }\n"
        "]\n\n"
        f"Flashcards to convert:\n{content}"
    )

    messages = [
        {'role': 'system', 'content': "You are a rigid JSON generator. You never explain. You only output valid JSON."},
        {'role': 'user', 'content': prompt}
    ]

    try:
        # Try prioritized models, prefer faster ones for quiz
        models_to_try = ["llama3.2:1b", "llama3.2", "llama3"]
        response = None
        
        for model in models_to_try:
            try:
                # Try with format='json' first
                print(f"Attempting quiz gen with {model} (JSON mode)...")
                response = ollama.chat(model=model, messages=messages, format='json')
                break
            except Exception as e:
                print(f"JSON mode failed for {model}: {e}. Retrying standard mode...")
                try:
                    response = ollama.chat(model=model, messages=messages)
                    break
                except:
                    continue
                
        if not response:
             print("No response from any model.")
             return []

        text = response['message']['content'].strip()
        print(f"Raw AI Quiz Response: {text[:500]}...") # Debug log
        
        # --- Robust Parsing ---
        data = []
        
        # 1. Clean wrappers
        text = re.sub(r'^```json\s*', '', text, flags=re.MULTILINE)
        text = re.sub(r'^```\s*', '', text, flags=re.MULTILINE)
        text = re.sub(r'\s*```$', '', text, flags=re.MULTILINE)
        
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            print(f"JSON Decode Failed. Attempting soft repair on: {text[:50]}...")
            # Try to find array bracket
            match = re.search(r'\[.*\]', text, re.DOTALL)
            if match:
                try:
                    data = json.loads(match.group())
                except:
                    pass

        # 2. Structure Validation
        valid_quiz = []
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    # Check keys
                    if 'question' in item and 'options' in item and 'answer' in item:
                         # Check types
                         if isinstance(item['options'], list) and len(item['options']) >= 2:
                             valid_quiz.append(item)
                elif isinstance(item, str):
                    # Edge case: Model returned list of strings? rare with strict json prompt but possible
                     pass

        if not valid_quiz and len(data) > 0:
             print("Parsed data but found no valid quiz objects.")

        # 3. Fallback: Regex Text Parsing (Detailed)
        if not valid_quiz:
             print("JSON failed. Attempting Regex Fallback...")
             valid_quiz = parse_quiz_text(text)

        # 4. Final Fallback: Deterministic Logic (No AI)
        if not valid_quiz:
             print("AI generation failed completely. Generating deterministic quiz...")
             valid_quiz = generate_deterministic_quiz(cards_list)

        return valid_quiz
        
    except Exception as e:
        print(f"Quiz generation error: {e}")
        # Even on error, try deterministic
        return generate_deterministic_quiz(cards_list)

def parse_quiz_text(text):
    """
    Aggressive fallback parser for unstructured quiz text.
    Looks for patterns like:
    1. Question?
    A. Option
    B. Option
    ...
    Answer: A
    """
    questions = []
    
    # Split text into blocks (assuming 2 newlines often separate questions)
    # If not, we might need a more complex regex.
    # Let's try splitting by something that looks like a new question start "1." or "Q1:"
    
    # Normalize
    text = text.replace("**", "") # Remove bolding
    
    # Pattern to find a question block:
    # Relaxed: Look for ANY text that ends with a newline and is followed by an Option A
    # We search for the "A. " pattern to identify the split between question and options
    
    # Strategy: Find "A." or "a)" or "(a)" markers
    opt_start_pattern = re.compile(r'\n\s*(?:[A-a][\.\)]|\([A-a]\))\s+')
    
    # Find all places where options start
    opt_starts = [m.start() for m in opt_start_pattern.finditer(text)]
    
    if not opt_starts:
        return []

    # Work backwards from each option start to find the question line
    # (This is heuristic but robust for unformated text)
    
    for i, opt_start in enumerate(opt_starts):
        # The block covering this question ends at the START of the NEXT question's first option (or text end)
        # But wait, we need to separate questions.
        pass

    # New Strategy: Split by "Q:" or Number if present, otherwise split by double newlines?
    # Let's try a regex that finds (Question) ... (Options) ... (Answer)
    
    # Regex for a full block
    # 1. Question text (non-greedy)
    # 2. Option A
    # 3. Option B ...
    # 4. Answer (Optional)
    
    blocks = []
    
    # Split text by things that look like Q1. or 1. OR just double newlines if we are desperate
    # But checking for Options is the most reliable anchor.
    
    # Let's find "A." markers and assume the text preceding it (up to previous answer or newline) is the question.
    
    # Simplified regex for Option line:
    opt_line_re = r'(?:[A-D][\.\)]|\([A-D]\))\s+.*'
    
    lines = text.split('\n')
    current_q = {"question": "", "options": [], "answer": "A"}
    
    for line in lines:
        line = line.strip()
        if not line: continue
        
        # Check if Option
        if re.match(r'^(?:[A-D][\.\)]|\([A-D]\))\s+', line, re.IGNORECASE):
            # It's an option.
            # Clean it
            val = re.sub(r'^(?:[A-D][\.\)]|\([A-D]\))\s+', '', line, flags=re.IGNORECASE).strip()
            # Determine letter
            letter_match = re.search(r'^([A-D])', line, re.IGNORECASE)
            letter = letter_match.group(1).upper() if letter_match else "A"
            current_q["options"].append(f"{letter}. {val}")
        
        # Check if Answer
        elif re.match(r'^Answer:?', line, re.IGNORECASE):
            # Extract letter
            ans_m = re.search(r'([A-D])', line, re.IGNORECASE)
            if ans_m:
                current_q["answer"] = ans_m.group(1).upper()
            
            # End of question block? Often yes.
            # But we push when we start a NEW question usually.
            
        else:
            # It's question text OR noise.
            # If we already have options, this means we are starting a NEW question (probably).
            if len(current_q["options"]) >= 2:
                # Save previous
                if current_q["question"]:
                    questions.append(current_q)
                current_q = {"question": line, "options": [], "answer": "A"}
            else:
                # Append to current question text
                if current_q["question"]:
                     current_q["question"] += " " + line
                else:
                     current_q["question"] = line
                     
    # Push last
    if len(current_q["options"]) >= 2 and current_q["question"]:
        questions.append(current_q)
        
    return questions

def generate_deterministic_quiz(cards_list):
    """
    Final Fallback: Generates a quiz programmatically without AI.
    Uses other cards' answers as distractors.
    """
    import random
    quiz = []
    
    # Get all potential answers for distractors
    all_answers = [c.get('back', 'N/A') for c in cards_list]
    
    for card in cards_list:
        question = card.get('front')
        correct_answer = card.get('back')
        
        # Select 3 distractors
        distractors = [a for a in all_answers if a != correct_answer]
        if len(distractors) < 3:
            # Not enough distractors, pad with generics
            distractors += ["None of the above", "All of the above", "Information missing"]
            distractors = distractors[:3] # Ensure max 3
        else:
            distractors = random.sample(distractors, 3)
            
        # Combine and shuffle
        options = distractors + [correct_answer]
        random.shuffle(options)
        
        # Find correct letter
        # options are strings, we map to A, B, C, D
        letters = ['A', 'B', 'C', 'D']
        correct_letter = 'A'
        
        formatted_options = []
        for i, opt in enumerate(options):
            formatted_options.append(f"{letters[i]}. {opt}")
            if opt == correct_answer:
                correct_letter = letters[i]
                
        quiz.append({
            "question": question,
            "options": formatted_options,
            "answer": correct_letter
        })
        
    return quiz
