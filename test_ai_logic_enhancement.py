import os
import sys
import django

# Set up Django environment
sys.path.append('d:\\DISHA\\learnbridge')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'learnbridge.settings')
django.setup()

from ai_core.ai_engine import get_tutor_system_prompt, get_hybrid_response_context
from ai_tutor.ai_logic import chat_with_ai

def test_system_prompt():
    print("--- Testing System Prompt ---")
    prompt_with_context = get_tutor_system_prompt(has_context=True)
    prompt_without_context = get_tutor_system_prompt(has_context=False)
    
    assert "DUAL-MODE FLEXIBILITY" in prompt_with_context
    assert "SMART CONTEXT DETECTION" in prompt_with_context
    assert "BLENDED ANSWERS" in prompt_with_context
    assert "COURSE AWARENESS" in prompt_with_context
    
    print("System prompt with context looks good.")
    
    assert "No specific course materials were found" in prompt_without_context
    print("System prompt without context looks good.")

def test_hybrid_context():
    # Since we can't easily mock the DB and vector store here without complex setup,
    # we'll just check if the function returns the expected structure.
    print("\n--- Testing Hybrid Response Context ---")
    context, system_prompt, is_course_aware = get_hybrid_response_context("What is Biology?", course_id=None)
    
    assert context == ""
    assert "No specific course materials were found" in system_prompt
    assert is_course_aware == False
    print("Hybrid context for no course_id looks good.")

if __name__ == "__main__":
    try:
        test_system_prompt()
        test_hybrid_context()
        print("\nAll logical checks passed!")
    except Exception as e:
        print(f"\nTest failed: {e}")
        sys.exit(1)
