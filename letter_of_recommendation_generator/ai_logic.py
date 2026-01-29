import ollama
from django.conf import settings

from .models import LetterRequest

def generate_recommendation_letter(data):
    """
    Generates a formal Letter of Recommendation based on the provided data.
    """
    
    # Helper to get display value from choices
    def get_display(choices, key):
        return dict(choices).get(key, key)

    purpose_display = get_display(LetterRequest.PURPOSE_CHOICES, data.get('purpose'))
    tone_display = get_display(LetterRequest.TONE_CHOICES, data.get('tone'))
    
    prompt = f"""
    You are a professional academic writer. Your task is to write a highly professional, formal Letter of Recommendation (LOR) for a student based on the following details.
    
    **Student Details:**
    - Name: {data.get('student_name')}
    - Course/Degree: {data.get('course_degree')}
    - Institution: {data.get('institution_name')}
    - Duration of Association: {data.get('duration_of_association')}
    
    **Attributes:**
    - Academic Performance: {data.get('academic_performance')}
    - Technical Skills: {data.get('technical_skills')}
    - Soft Skills: {data.get('soft_skills')}
    - Achievements/Projects: {data.get('achievements')}
    
    **Letter Context:**
    - Purpose: {purpose_display}
    - Tone: {tone_display}
    
    **Guidelines:**
    1. **Format**: Standard formal letter format. Start with "To Whom It May Concern," or a generic formal salutation if specific recipient is unknown. 
    2. **Tone**: {tone_display}. Professional, academic, and respectful. NO emojis. NO casual language.
    3. **Content**:
       - Introduce the recommender's relationship with the student.
       - Highlight the student's academic prowess and technical skills.
       - Elaborate on soft skills and personal qualities.
       - key achievements should be woven into the narrative naturally.
       - Conclude with a strong recommendation.
    4. **Structure**: clear paragraphs, coherent flow.
    5. **Output**: Return ONLY the body of the letter. Do not include your own "Here is the letter" texts.
    
    Write the letter now.
    """

    try:
        # Use 'llama3' as seen in test_ollama.py, or fallback to a default if configured differently
        model_name = getattr(settings, 'OLLAMA_MODEL', 'llama3') 
        
        response = ollama.chat(model=model_name, messages=[{'role': 'user', 'content': prompt}])
        content = response['message']['content']
        return content
    except Exception as e:
        # FALLBACK MODE: Generate a template letter if AI is offline
        print(f"AI Connection Error: {e}. Using fallback template.")
        
        fallback_letter = f"""To Whom It May Concern,

I am writing to enthusiastically recommend {data.get('student_name')} for their application regarding {purpose_display.lower()}. 

I have known {data.get('student_name')} for {data.get('duration_of_association')} in my capacity as a faculty member at {data.get('institution_name')}, where they pursued their {data.get('course_degree')}. During this time, I have been consistently impressed by their dedication and academic excellence.

{data.get('student_name')} has demonstrated strong performance, specifically noted in their {data.get('academic_performance')}. Beyond academics, they possess remarkable technical skills, including {data.get('technical_skills')}. 

What truly sets them apart, however, are their soft skills. They have shown {data.get('soft_skills')}, which makes them a valuable asset to any team or institution. Their achievements, such as {data.get('achievements')}, further speak to their capability and drive.

I strongly recommend {data.get('student_name')} without reservation. I am confident they will excel in their future endeavors.

Sincerely,

[Recommender Name]
[Title]
{data.get('institution_name')}"""
        return fallback_letter
