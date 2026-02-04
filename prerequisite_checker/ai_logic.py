import ollama
import json
import re

SYSTEM_PROMPT = (
    "You are the Prerequisite Checker AI for LearnBridge.\n"
    "PURPOSE: Analyze advanced topics questions.\n"
    "OUTPUT FORMAT: You must always return strictly valid JSON."
)

def extract_json(text):
    """
    Robustly extracts JSON object from text by finding the first { and last }.
    """
    try:
        # Find start and end of JSON object
        start = text.find('{')
        end = text.rfind('}') + 1
        
        if start != -1 and end != -1:
            json_str = text[start:end]
            return json.loads(json_str)
        return None
    except Exception as e:
        print(f"JSON Parsing Error: {e}")
        return None

def get_prerequisites(topic, context=None):
    """
    Analyzes a topic and returns a list of prerequisite concepts.
    Returns: list of strings e.g. ["Linear Algebra", "Calculus"]
    """
    prompt = f"Identify the top 3-5 critical prerequisite concepts required to understand: '{topic}'."
    
    if context:
        prompt += f"\n\nContext Content:\n{context}\n\n"
        prompt += "Based on the specific content above, what prior knowledge is needed?"

    prompt += "\nReturn ONLY a JSON object with a single key 'prerequisites' containing a list of strings.\n"
    prompt += "Example: {\"prerequisites\": [\"Concept A\", \"Concept B\"]}"
    
    try:
        response = ollama.chat(
            model="llama3",
            messages=[
                {'role': 'system', 'content': SYSTEM_PROMPT},
                {'role': 'user', 'content': prompt}
            ]
        )
        content = response['message']['content']
        print(f"AI Response (Prereqs): {content}") # Debug print
        
        data = extract_json(content)
        if data:
            return data.get('prerequisites', [])
        return []
    except Exception as e:
        print(f"Error getting prerequisites: {e}")
        return []

def generate_questions(concepts):
    """
    Generates a diagnostic question for each concept.
    Returns: list of dicts [{'concept': 'X', 'question': 'Y'}]
    """
    if not concepts:
        return []

    concepts_str = ", ".join(concepts)
    prompt = (
        f"For each of these concepts: {concepts_str}, generate ONE conceptual diagnostic question "
        "to test basic understanding. Do not ask for definitions, ask for application or intuition.\n"
        "Return ONLY a JSON object with a key 'questions' containing a list of objects.\n"
        "Each object must have 'concept' and 'question' keys.\n"
        "Example: {\"questions\": [{\"concept\": \"Linear Algebra\", \"question\": \"Why do we use...\"}]}"
    )

    try:
        response = ollama.chat(
            model="llama3",
            messages=[
                {'role': 'system', 'content': SYSTEM_PROMPT},
                {'role': 'user', 'content': prompt}
            ]
        )
        content = response['message']['content']
        print(f"AI Response (Questions): {content}") # Debug print

        data = extract_json(content)
        if data:
            return data.get('questions', [])
        return []
    except Exception as e:
        print(f"Error generating questions: {e}")
        return []

def evaluate_readiness(responses):
    """
    Evaluates student answers.
    responses: list of dicts [{'concept': 'X', 'question': 'Y', 'answer': 'Z'}]
    Returns: dict {'score': 75, 'results': [{'concept': 'X', 'status': 'Strong', 'feedback': '...'}]}
    """
    if not responses:
        return {}
        
    prompt = (
        "Evaluate the following student answers to diagnostic questions.\n"
        "For each answer, determine if the understanding is 'Strong', 'Weak', or 'Missing'.\n"
        "Also provide specific feedback.\n"
        "Calculate an overall readiness score (0-100).\n\n"
        "Student Data:\n" + json.dumps(responses) + "\n\n"
        "Return ONLY a JSON object with keys: 'score' (int) and 'results' (list of objects).\n"
        "Each result object must have 'concept', 'status', 'feedback'."
    )
    
    try:
        response = ollama.chat(
            model="llama3",
            messages=[
                {'role': 'system', 'content': SYSTEM_PROMPT},
                {'role': 'user', 'content': prompt}
            ]
        )
        content = response['message']['content']
        print(f"AI Response (Evaluation): {content}") # Debug print

        data = extract_json(content)
        if data:
            return data
        return {'score': 0, 'results': []}
    except Exception as e:
        print(f"Error evaluating readiness: {e}")
        return {'score': 0, 'results': []}
