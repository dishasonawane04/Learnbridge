import json
import re
import asyncio
from django.conf import settings
import ollama

async def generate_questions(topic="Python", level="Foundation", num_questions=5):
    # Add strong randomness using timestamp + random seed
    import random
    import time
    
    # Create a unique seed based on timestamp and random number
    timestamp_seed = int(time.time() * 1000) % 10000
    random_seed = random.randint(1, 10000)
    combined_seed = timestamp_seed + random_seed
    
    # Define topic-specific areas to vary questions
    topic_areas = {
        "Python": ["syntax", "data structures", "functions", "loops", "conditionals", "OOP", "modules", "file handling", "exceptions", "comprehensions"],
        "Math": ["algebra", "geometry", "calculus", "statistics", "probability", "trigonometry", "number theory", "logic", "sets", "functions"],
        "Data Science": ["pandas", "numpy", "visualization", "statistics", "machine learning", "data cleaning", "exploratory analysis", "modeling", "evaluation", "preprocessing"]
    }
    
    # Select random subtopics for variety
    subtopics = topic_areas.get(topic, ["general concepts"])
    selected_subtopics = random.sample(subtopics, min(3, len(subtopics)))
    subtopic_hint = f"Focus on these areas: {', '.join(selected_subtopics)}."
    
    # Build difficulty-specific examples
    difficulty_examples = {
        "Foundation": """
        Example for Foundation level:
        Question: "What does the print() function do in Python?"
        Options: ["Displays output to the screen", "Saves data to a file", "Deletes a variable", "Creates a loop"]
        Answer: "Displays output to the screen"
        """,
        "Developing": """
        Example for Developing level:
        Question: "What will be the output of: len([1, 2, 3, 4])?"
        Options: ["4", "3", "5", "Error"]
        Answer: "4"
        """,
        "Proficient": """
        Example for Proficient level:
        Question: "Which data structure provides O(1) average time complexity for lookups?"
        Options: ["Dictionary (hash table)", "List", "Tuple", "Set (for ordered lookups)"]
        Answer: "Dictionary (hash table)"
        """,
        "Advanced": """
        Example for Advanced level:
        Question: "What is the purpose of the __slots__ attribute in Python classes?"
        Options: ["Reduces memory usage by preventing __dict__ creation", "Speeds up method calls", "Enables multiple inheritance", "Allows dynamic attribute addition"]
        Answer: "Reduces memory usage by preventing __dict__ creation"
        """,
        "Mastery": """
        Example for Mastery level:
        Question: "In CPython, what is the GIL's primary impact on multi-threaded programs?"
        Options: ["Prevents true parallel execution of Python bytecode", "Improves single-threaded performance", "Enables automatic memory management", "Reduces context switching overhead"]
        Answer: "Prevents true parallel execution of Python bytecode"
        """
    }
    
    example = difficulty_examples.get(level, "")
    
    prompt = f"""
    Create {num_questions} quiz questions for {topic} at {level} level.
    Focus areas: {', '.join(selected_subtopics)}
    
    EXPECTED FORMAT:
    Q: [Question Text]
    O1: [Option 1]
    O2: [Option 2]
    O3: [Option 3]
    O4: [Option 4]
    A: [Exact text of correct option]

    RULES:
    1. STRICTLY follow the Q/O/A format above.
    2. Be technically accurate for {level} level.
    3. NO hallucinations (e.g., 'del' does NOT create a loop).
    """

    try:
        client = ollama.AsyncClient()
        response = await client.chat(
            model=settings.OLLAMA_MODEL_TEXT,
            messages=[{"role": "user", "content": prompt}],
            options={
                "temperature": 0.4,
                "top_p": 0.9,
                "seed": combined_seed
            }
        )

        text = response["message"]["content"].strip()
        print(f"DEBUG LLM Output: {text[:200]}...")

        # 1. Ultra-Robust Text Parser
        raw_questions = []
        # Support variations: Q1:, Question 1:, Q:, etc.
        blocks = re.split(r'(?i)(?:^|\n)\s*(?:Q|Question)(?:\s*\d+)?[:.)\\s\\-]+', text)
        
        print(f"DEBUG: Found {len(blocks)} blocks")
        
        for block_idx, block in enumerate(blocks):
            if not block.strip() or len(block) < 20: 
                continue
            
            print(f"DEBUG: Processing block {block_idx}: {block[:100]}...")
            
            # Split block into lines and clean them
            lines = [l.strip() for l in block.split('\n') if l.strip()]
            if not lines: continue

            # Question text is usually the first line
            q_text = lines[0]
            
            # Extract options (Support O1, A, 1), -, etc)
            options = []
            # Answer text
            answer = ""

            # More flexible option pattern - matches O1:, O1., O1), 1:, 1., 1), A:, etc.
            option_pattern = r'(?i)^(?:O|Option|Choice)?(?:\s*[a-d1-4])?[:.)\\s\\-]+'

            for line in lines[1:]:
                # Identify if this is the Answer line
                if re.match(r'(?i)^\s*A(?:nswer)?[:.)\\s]', line):
                    # Extract answer text after the prefix
                    answer = re.sub(r'(?i)^\s*A(?:nswer)?[:.)\\s]+', '', line).strip()
                    print(f"DEBUG: Found answer: {answer}")
                    continue
                
                # Identify if this is an Option line
                # Options usually look like O1:, 1), a., or just text if it followed O1:
                if re.match(option_pattern, line):
                    opt_text = re.sub(option_pattern, '', line).strip()
                    if opt_text and opt_text != q_text and opt_text not in options and len(opt_text) > 1:
                        options.append(opt_text)
                        print(f"DEBUG: Found option: {opt_text}")

            # Fallback for answer if not explicitly labeled with A:
            if not answer:
                # Look for line starting with A: anywhere
                a_match = re.search(r'(?i)(?:\n|^)\s*A(?:nswer)?:\s*(.*)', block)
                if a_match:
                    answer = a_match.group(1).strip()
                    print(f"DEBUG: Found answer via regex: {answer}")

            # Final Cleanup and Matching
            if q_text and len(options) >= 2:
                # If answer exists, find the closest matching option
                if answer:
                    answer = re.sub(option_pattern, '', answer).strip()
                    # Case-insensitive match find
                    matched = False
                    for opt in options:
                        if answer.lower() == opt.lower() or answer.lower() in opt.lower() or opt.lower() in answer.lower():
                            answer = opt
                            matched = True
                            print(f"DEBUG: Matched answer to option: {answer}")
                            break
                    
                    if not matched:
                        # If no match, default to first option (fragile but prevents crash)
                        print(f"DEBUG WARNING: Answer '{answer}' didn't match any option, using first option")
                        answer = options[0]
                else:
                    # If no answer found, can't reliably use this question
                    print(f"DEBUG: Skipping question - no answer found")
                    continue

                raw_questions.append({
                    "question": q_text,
                    "options": options[:4],
                    "answer": answer
                })
                print(f"DEBUG: Added question: {q_text[:50]}... with {len(options[:4])} options")
            else:
                print(f"DEBUG: Skipping question - insufficient data (q_text={bool(q_text)}, options={len(options)})")


        if not raw_questions:
             print("DANGER: Text parser failed. Trying fallback.")
             return fallback_questions(num_questions)

        # 🔒 HALLUCINATION FILTER (Final Sweep)
        clean_questions = []
        for q in raw_questions:
            q_text = q["question"].lower()
            bad_keywords = ["del", "try", "except", "if", "with", "len", "type"]
            options_smash = any("loop" in opt.lower() for opt in q["options"])
            
            # If question is about a non-looping keyword but options mention loops, REJECT
            is_unsafe = any(k in q_text for k in bad_keywords) and options_smash
            if is_unsafe:
                print(f"REJECTED hallucinated question: {q['question']}")
                continue
            
            clean_questions.append(q)

        if not clean_questions:
            return fallback_questions(num_questions)

        return clean_questions[:num_questions]

    except Exception as e:
        print(f"Error generating questions: {e}")
        return fallback_questions(num_questions)


async def generate_feedback(score, total, wrong_topics):

    percentage = (score / total) * 100 if total > 0 else 0

    if percentage >= 70:
        advice = "Great job! You're ready for the next challenge."
    elif percentage >= 50:
        advice = "Good effort! Review your mistakes and try again."
    else:
        advice = "Don't give up! Focus on the basics and keep practicing."

    prompt = f"""
    You are an expert tutor. Provide brief, supportive feedback for a student based on their quiz performance.
    
    Score: {score}/{total}
    Pass threshold: 70%
    Questions they got WRONG: {wrong_topics}
    
    CRITICAL RULES:
    1. If Score is {total}/{total} (Perfect Score): 
       - Be 100% celebratory and congratulatory.
       - DO NOT mention "reviewing" or "struggling" with any topics.
       - Provide one very high-level, "legendary" Python challenge or concept for them to research next (e.g., meta-programming, async internals).
    2. If Score is less than {total}/{total}:
       - Mention the specific topics in {wrong_topics} they struggled with.
       - Give actionable advice (e.g., "Focus on how decorators wrap functions").
    3. Stay under 3 sentences total.
    """

    try:
        client = ollama.AsyncClient()
        response = await client.chat(
            model=settings.OLLAMA_MODEL_TEXT,
            messages=[{"role": "user", "content": prompt}]
        )
        return response["message"]["content"].strip()
    except Exception:
        return advice


async def explain_answer(question, correct_answer, user_answer):
    prompt = f"""
    You are an expert tutor for University (UG/PG) students. 
    Explain why the following is true in simple, professional, and analytical language.
    
    Question: {question}
    Correct Answer: {correct_answer}
    Student Answer: {user_answer}
    
    FORMAT YOUR RESPONSE IN THESE EXACT SECTIONS:
    
    ### 💡 In Simple Words
    [One or two sentences explaining the concept clearly]
    
    ### 🌍 Why it Matters
    [Explain the real-world application or why this concept is fundamental to the field]
    
    ### ⚠️ Common Mistakes
    [Mention common misconceptions or errors students make with this topic]
    
    ### 📝 Key Takeaway
    [A single summary sentence]
    """

    try:
        client = ollama.AsyncClient()
        response = await client.chat(
            model=settings.OLLAMA_MODEL_TEXT,
            messages=[{"role": "user", "content": prompt}]
        )
        return response["message"]["content"].strip()
    except Exception:
        return f"The correct answer is '{correct_answer}' because it best fits the criteria for {question}."


def fallback_questions(num=5):
    import random
    pool = [
        {
            "question": "What is the primary purpose of the GIL (Global Interpreter Lock) in CPython?",
            "options": ["To ensure thread safety for memory management", "To speed up multi-core performance", "To allow threads to run in parallel", "To prevent memory leaks"],
            "answer": "To ensure thread safety for memory management"
        },
        {
            "question": "Which of these is a Python 'dunder' method used for initialization?",
            "options": ["__init__", "__start__", "__new__", "__main__"],
            "answer": "__init__"
        },
        {
            "question": "In Python, which keyword is used to handle exceptions?",
            "options": ["try", "catch", "handle", "throw"],
            "answer": "try"
        },
        {
            "question": "What is the result of 2 ** 3 in Python?",
            "options": ["8", "6", "9", "5"],
            "answer": "8"
        },
        {
            "question": "Which data structure is best for storing unique items with fast membership testing?",
            "options": ["Set", "List", "Tuple", "Dict (values)"],
            "answer": "Set"
        },
        {
            "question": "Which of these is NOT a Python data type?",
            "options": ["List", "Dictionary", "Tuple", "Array"],
            "answer": "Array"
        },
        {
            "question": "How do you start a while loop in Python?",
            "options": ["while x > y:", "while (x > y)", "while x > y", "if x > y:"],
            "answer": "while x > y:"
        },
        {
            "question": "What is the correct file extension for Python files?",
            "options": [".pt", ".pyth", ".py", ".pyt"],
            "answer": ".py"
        },
        {
            "question": "Which operator is used for exponentiation?",
            "options": ["^", "**", "//", "*"],
            "answer": "**"
        },
        {
            "question": "What is the result of 3 * '7'?",
            "options": ["21", "777", "Error", "37"],
            "answer": "777"
        }
    ]
    return random.sample(pool, min(num, len(pool)))
