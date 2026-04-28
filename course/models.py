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
    executive_summary = models.TextField(blank=True, help_text="Cached AI-generated summary of the course")
    
    page_count = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)
    
    # Chunking State
    flashcard_chunk_index = models.PositiveIntegerField(default=0)
    
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
            from ai_core.services import process_course_notes_into_knowledge_store
            try:
                extracted_data = parse_document(self.uploaded_file.path)
                if extracted_data:
                    # extracted_data is [{'page_number': 1, 'text': '...'}, ...]
                    full_text = "\n".join([p['text'] for p in extracted_data])
                    page_count = len(extracted_data)
                    
                    Course.objects.filter(pk=self.pk).update(
                        extracted_text=full_text,
                        page_count=page_count,
                        executive_summary="" # Clear cache on new material
                    )
                    
                    # Also process into KnowledgeStore for RAG
                    process_course_notes_into_knowledge_store(self.pk, extracted_data)
            except Exception as e:
                print(f"Error extracting text or indexing: {e}")

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

def course_material_upload_path(instance, filename):
    """Dynamic path: media/courses/{course_id}/materials/{filename}"""
    # Defensive check for unit-only materials (legacy support)
    course_id = instance.course.id if instance.course else (instance.unit.course.id if instance.unit else 'misc')
    return f'courses/{course_id}/materials/{filename}'

class CourseMaterial(models.Model):
    FILE_TYPES = (
        ('pdf', 'PDF Document'),
        ('ppt', 'PowerPoint'),
        ('image', 'Image/Diagram'),
        ('text', 'Text/Markdown'),
    )
    
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='course_materials', null=True, blank=True)
    unit = models.ForeignKey(CourseUnit, on_delete=models.CASCADE, related_name='materials', null=True, blank=True)
    file = models.FileField(upload_to=course_material_upload_path)
    display_name = models.CharField(max_length=255, blank=True, help_text="Custom name for the document")
    file_type = models.CharField(max_length=10, choices=FILE_TYPES)
    extracted_text = models.TextField(blank=True, help_text="AI-extracted text content for context")
    summary = models.TextField(blank=True, help_text="AI-generated summary")
    key_topics = models.JSONField(default=list, blank=True, help_text="List of important topics/concepts")
    created_at = models.DateTimeField(auto_now_add=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def get_display_name(self):
        """Returns user-set display_name or a clean version of the filename."""
        if self.display_name:
            return self.display_name
        import os
        return os.path.basename(self.file.name)

    
    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        # Automate extraction and RAG processing
        if is_new and self.file:
            try:
                # 1. Extract Text
                from .utils.extraction import extract_text_from_path
                extracted = extract_text_from_path(self.file.path)
                if extracted:
                    self.extracted_text = extracted
                    # Use update to avoid triggering save() again recursively
                    CourseMaterial.objects.filter(pk=self.pk).update(extracted_text=extracted)
                
                # 2. RAG Processing
                from ai_engine.course_processor import process_document
                cid = self.course.id if self.course else self.unit.course.id
                process_document(self.file.path, cid)
                
                # 3. Consolidate into CourseNotes
                from core.ai.services import CourseContextEngine
                CourseContextEngine.consolidate_course_notes(cid)

                # 4. Invalidate cache
                if self.course:
                    self.course.executive_summary = ""
                    self.course.save(update_fields=['executive_summary'])
                elif self.unit and self.unit.course:
                    self.unit.course.executive_summary = ""
                    self.unit.course.save(update_fields=['executive_summary'])

                # 5. Trigger Concept Map Update
                try:
                    from .services.concept_map import ConceptMapService
                    ConceptMapService.generate_for_course(cid, self.course.user if self.course else self.unit.course.user)
                except Exception as ce:
                    logger.error(f"Concept Map update failed for Material {self.id}: {ce}")
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Automated processing failed for Material {self.id}: {e}")

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

class ConceptMap(models.Model):
    """Stores visual concept map data generated from course notes"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='concept_maps')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='concept_maps')
    note = models.ForeignKey('notes.Note', on_delete=models.CASCADE, related_name='concept_maps', null=True, blank=True)
    data = models.JSONField(default=dict, help_text="Cytoscape.js compatible JSON data")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('course', 'note')

    def __str__(self):
        return f"Map for {self.course.title}"

class QuizChunk(models.Model):
    """Stores course text segments for incremental quiz generation"""
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='quiz_chunks')
    content = models.TextField()
    is_used = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"Chunk {self.order} for {self.course.title}"

class FlashcardChunk(models.Model):
    """Stores course text segments for incremental flashcard generation"""
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='flashcard_chunks')
    content = models.TextField()
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"FC Chunk {self.order} for {self.course.title}"

# --- Assignment / Task System Models ---

class TaskAssignment(models.Model):
    TASK_TYPE_CHOICES = (
        ('quiz', 'Quiz'),
        ('topic', 'Topic Revision'),
        ('flashcards', 'Flashcards Practice'),
        ('summary', 'Summary Reading'),
        ('custom', 'Custom Task'),
    )
    PRIORITY_CHOICES = (
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    )
    
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='assignments')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    task_type = models.CharField(max_length=20, choices=TASK_TYPE_CHOICES)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_assignments')
    reference_id = models.CharField(max_length=255, blank=True, null=True, help_text="ID or name of the specific topic/quiz")
    
    deadline = models.DateTimeField(null=True, blank=True)
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.title} ({self.get_task_type_display()})"

class TaskSubmission(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('overdue', 'Overdue'),
        ('completed_late', 'Completed Late'),
    )
    
    assignment = models.ForeignKey(TaskAssignment, on_delete=models.CASCADE, related_name='submissions')
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='task_submissions')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    score = models.FloatField(null=True, blank=True, help_text="If applicable, score achieved")
    remarks = models.TextField(blank=True)
    
    class Meta:
        unique_together = ('assignment', 'student')
        
    def __str__(self):
        return f"{self.student.username} - {self.assignment.title} - {self.status}"
