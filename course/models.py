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
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.course.title} - {self.title}"

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
