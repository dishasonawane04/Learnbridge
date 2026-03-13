import json
from django.conf import settings
from ai_engine.llm import ask_llm

def generate_concept_map_data(text):
    """
    Analyzes text and returns a hierarchical concept map structure.
    Output format is compatible with Cytoscape.js.
    """
    # 1. Truncate text to 2500 chars to ensure local CPU generation completes before timeout
    text = text[:2500]
    
    system_prompt = """You are an Educational Data Architect.
    Analyze the provided text and extract a hierarchical concept map.
    
    STRICT REQUIREMENTS:
    1. Output ONLY a valid JSON object.
    2. Identify the 'Main Topic'.
    3. Identify key 'Subtopics'.
    4. Identify 'Concepts' under each subtopic.
    5. Define clear relationships (edges) between them.
    6. MAXIMUM 15 NODES TOTAL. Keep it concise, high-level, and fast to generate.
    
    JSON FORMAT:
    {
      "nodes": [
        {"id": "topic", "label": "Main Topic", "type": "main"},
        {"id": "sub1", "label": "Subtopic 1", "type": "subtopic"},
        {"id": "concept1", "label": "Concept A", "type": "concept"}
      ],
      "edges": [
        {"source": "topic", "target": "sub1", "label": "contains"},
        {"source": "sub1", "target": "concept1", "label": "includes"}
      ]
    }"""
    
    user_prompt = f"""Generate a Concept Map (MAX 15 NODES) from this text:
    
    TEXT:
    {text}
    
    JSON:"""
    
    try:
        response = ask_llm(user_prompt, system_prompt=system_prompt)
        
        # Check for error responses from ask_llm
        if response.startswith("Error:") or response.startswith("AI Error:"):
            print(f"Concept Map Generation skipped: {response}")
            return {}

        # Simple extraction strategy - look for the JSON block
        import re
        # Try to find JSON between triple backticks first
        json_match = re.search(r'```(?:json)?\s*({[\s\S]*?})\s*```', response)
        if json_match:
            clean_json = json_match.group(1)
        else:
            # Fallback to finding the first { and last }
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1
            if start_idx != -1 and end_idx != -1:
                clean_json = response[start_idx:end_idx]
            else:
                print(f"Concept Map Error: No JSON found in AI response. Snippet: {response[:100]}...")
                return {}

        try:
            return json.loads(clean_json)
        except json.JSONDecodeError as je:
            print(f"Concept Map Error: JSON Decode failed: {je}")
            # Potentially fix common JSON issues here if needed
            return {}
            
    except Exception as e:
        print(f"Concept Map Generation Error: {e}")
        return {}
