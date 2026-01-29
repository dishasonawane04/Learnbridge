from django.db import models

class LetterRequest(models.Model):
    PURPOSE_CHOICES = [
        ('higher_studies', 'Higher Studies (Masters/PhD)'),
        ('job', 'Job Application'),
        ('scholarship', 'Scholarship Application'),
        ('research', 'Research Position'),
        ('other', 'Other'),
    ]

    TONE_CHOICES = [
        ('academic', 'Academic Focused'),
        ('research', 'Research Oriented'),
        ('industry', 'Industry/Professional'),
        ('strong', 'Strongly Recommended'),
        ('neutral', 'Balanced/Neutral'),
    ]

    # Student Information
    student_name = models.CharField(max_length=255)
    course_degree = models.CharField(max_length=255, help_text="e.g. B.Tech Computer Science")
    institution_name = models.CharField(max_length=255)
    duration_of_association = models.CharField(max_length=100, help_text="e.g. 2 years, 2022-2024")
    
    # Performance & Skills
    academic_performance = models.TextField(help_text="Grades, class rank, specific subject strengths")
    technical_skills = models.TextField(help_text="Programming languages, tools, technologies")
    soft_skills = models.TextField(help_text="Communication, leadership, teamwork")
    achievements = models.TextField(blank=True, help_text="Projects, internships, publications, awards")
    
    # Letter Specifics
    purpose = models.CharField(max_length=50, choices=PURPOSE_CHOICES, default='higher_studies')
    tone = models.CharField(max_length=50, choices=TONE_CHOICES, default='academic')
    
    # Generated Content
    generated_letter = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"LOR for {self.student_name} - {self.get_purpose_display()}"
