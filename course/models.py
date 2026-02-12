from django.db import models
from django.contrib.auth.models import User

class Course(models.Model):
    LEVEL_CHOICES = (
        ('UG', 'Undergraduate'),
        ('PG', 'Postgraduate'),
        ('PROF', 'Professional'),
    )
    DIFFICULTY_CHOICES = (
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='courses')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    subject = models.CharField(max_length=100, blank=True, help_text="e.g. Machine Learning, Cardiology")
    level = models.CharField(max_length=10, choices=LEVEL_CHOICES, default='UG')
    difficulty = models.CharField(max_length=20, choices=DIFFICULTY_CHOICES, default='beginner')
    color_theme = models.CharField(max_length=20, default='#6366f1', help_text="Hex code for UI personalization")
    
    # New Fields for Central AI Engine
    uploaded_file = models.FileField(upload_to='courses/', null=True, blank=True)
    extracted_text = models.TextField(blank=True)
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='uploaded_courses')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        # Handle uploaded_by if not set
        if not self.uploaded_by and self.user:
            self.uploaded_by = self.user
            
        # Check if file has changed
        is_new_file = False
        if self.pk:
            old_instance = Course.objects.get(pk=self.pk)
            if old_instance.uploaded_file != self.uploaded_file:
                is_new_file = True
        else:
            if self.uploaded_file:
                is_new_file = True

        super().save(*args, **kwargs)

        # Trigger extraction if file is new or modified
        if is_new_file and self.uploaded_file:
            from .services.document_parser import parse_document
            try:
                extracted = parse_document(self.uploaded_file.path)
                if extracted:
                    Course.objects.filter(pk=self.pk).update(extracted_text=extracted)
            except Exception as e:
                print(f"Error extracting text: {e}")

    def __str__(self):
        return self.title

class CourseUnit(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='units')
    title = models.CharField(max_length=255)
    overview = models.TextField(blank=True, help_text="Syllabus/learning objectives for this unit")
    content = models.TextField(blank=True, help_text="Main content/notes for this unit")
    uploaded_file = models.FileField(upload_to='course_materials/', blank=True, null=True, help_text="Optional file upload for the lesson")
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.course.title} - {self.title}"

    # Alias for clarity in other parts of the system if needed
    @property
    def is_lesson(self):
        return True

class CourseMaterial(models.Model):
    FILE_TYPES = (
        ('pdf', 'PDF Document'),
        ('ppt', 'PowerPoint'),
        ('image', 'Image'),
        ('audio', 'Audio'),
        ('text', 'Text/Markdown'),
    )
    
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='course_materials', null=True, blank=True)
    unit = models.ForeignKey(CourseUnit, on_delete=models.CASCADE, related_name='materials', null=True, blank=True)
    file = models.FileField(upload_to='course_materials/')
    file_type = models.CharField(max_length=10, choices=FILE_TYPES)
    extracted_text = models.TextField(blank=True, help_text="AI-extracted text content for context")
    summary = models.TextField(blank=True, help_text="AI-generated summary")
    key_topics = models.JSONField(default=list, blank=True, help_text="List of important topics/concepts")
    created_at = models.DateTimeField(auto_now_add=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        if self.unit:
            return f"{self.unit.title} Material ({self.file_type})"
        return f"{self.course.title} Material ({self.file_type})"

class UserUnitCompletion(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='unit_completions')
    unit = models.ForeignKey(CourseUnit, on_delete=models.CASCADE, related_name='completions')
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'unit')

    def __str__(self):
        return f"{self.user.username} completed {self.unit.title}"

# --- Knowledge Layer Models ---

class ConceptNode(models.Model):
    """Atomic topics within a unit for granular mastery tracking"""
    TAXONOMY_CHOICES = (
        ('remember', 'Remembering'),
        ('understand', 'Understanding'),
        ('apply', 'Applying'),
        ('analyze', 'Analyzing'),
        ('evaluate', 'Evaluating'),
        ('create', 'Creating'),
    )
    
    unit = models.ForeignKey(CourseUnit, on_delete=models.CASCADE, related_name='concepts')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    taxonomy_level = models.CharField(max_length=20, choices=TAXONOMY_CHOICES, default='remember')
    difficulty_index = models.FloatField(default=0.5, help_text="0.0 to 1.0 (Easy to Hard)")
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.unit.title} - {self.title}"

class KnowledgeRelationship(models.Model):
    """Prerequisites and dependencies between concepts"""
    RELATION_TYPES = (
        ('prereq', 'Prerequisite'),
        ('related', 'Related'),
        ('part_of', 'Part Of'),
    )
    
    source = models.ForeignKey(ConceptNode, on_delete=models.CASCADE, related_name='dependencies')
    target = models.ForeignKey(ConceptNode, on_delete=models.CASCADE, related_name='dependents')
    relation_type = models.CharField(max_length=15, choices=RELATION_TYPES, default='prereq')

    class Meta:
        unique_together = ('source', 'target')

class UserConceptMastery(models.Model):
    """Granular mastery score for a specific concept"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    concept = models.ForeignKey(ConceptNode, on_delete=models.CASCADE)
    score = models.FloatField(default=0.0, help_text="Mastery score 0-100")
    confidence_level = models.FloatField(default=0.0, help_text="User self-reported confidence 0-100")
    last_practiced = models.DateTimeField(auto_now=True)
    retention_index = models.FloatField(default=1.0, help_text="Estimated memory retention (0-1)")

    class Meta:
        unique_together = ('user', 'concept')
        verbose_name_plural = "User concept masteries"

class UserCourseReadiness(models.Model):
    """Predictive metric for overall exam readiness in a course"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    readiness_percentage = models.FloatField(default=0.0)
    consistency_score = models.FloatField(default=0.0, help_text="Study streak/consistency factor")
    exam_date_goal = models.DateField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'course')
        verbose_name_plural = "User course readinesses"

class StudyActivity(models.Model):
    """Tracks daily active engagement for heatmap and streaks"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    date = models.DateField(auto_now_add=True)
    engagement_points = models.PositiveIntegerField(default=0, help_text="Points based on activity type")
    activity_type = models.CharField(max_length=50, help_text="e.g., unit_read, quiz_attempt, ai_chat")

    class Meta:
        verbose_name_plural = "Study activities"
        unique_together = ('user', 'course', 'date')

class AIStudyInsight(models.Model):
    """Auto-generated daily learning tips for the user"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    content = models.TextField()
    insight_type = models.CharField(max_length=20, default='tip') # tip, warning, motivation
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-created_at']

class CourseContext(models.Model):
    """Aggregate knowledge context for a course"""
    course = models.OneToOneField(Course, on_delete=models.CASCADE, related_name='context')
    important_concepts = models.JSONField(default=list, blank=True)
    glossary_terms = models.JSONField(default=dict, blank=True)
    embeddings_status = models.BooleanField(default=False)
    last_processed = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Context for {self.course.title}"

class CourseNotes(models.Model):
    """Simplified central store for all extracted text in a course"""
    course = models.OneToOneField(Course, on_delete=models.CASCADE, related_name='notes')
    extracted_text = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Notes for {self.course.title}"

class StudySession(models.Model):
    """Tracks engagement and activity per course"""
    ACTIVITY_CHOICES = (
        ('quiz', 'Quiz'),
        ('tutor', 'AI Tutor'),
        ('reading', 'Reading'),
        ('flashcards', 'Flashcards'),
        ('research', 'Research'),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    activity_type = models.CharField(max_length=20, choices=ACTIVITY_CHOICES)
    time_spent = models.PositiveIntegerField(help_text="Time spent in minutes")
    date = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.activity_type} on {self.date}"
