from django.db import models
from django.contrib.auth.models import User

class Course(models.Model):
    LEVEL_CHOICES = (
        ('UG', 'Undergraduate'),
        ('PG', 'Postgraduate'),
        ('PROF', 'Professional'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='courses')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    level = models.CharField(max_length=10, choices=LEVEL_CHOICES, default='UG')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

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
    
    unit = models.ForeignKey(CourseUnit, on_delete=models.CASCADE, related_name='materials')
    file = models.FileField(upload_to='course_materials/')
    file_type = models.CharField(max_length=10, choices=FILE_TYPES)
    extracted_text = models.TextField(blank=True, help_text="AI-extracted text content for context")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.unit.title} Material ({self.file_type})"

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
