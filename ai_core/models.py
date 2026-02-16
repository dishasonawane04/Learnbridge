from django.db import models
from course.models import Course

class KnowledgeStore(models.Model):
    """
    Stores document chunks and their high-dimensional embeddings.
    """
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='knowledge_chunks')
    content = models.TextField()
    embedding = models.JSONField()  # Store list of floats
    metadata = models.JSONField(default=dict, blank=True) # Source filename, page number, etc.
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Chunk for {self.course.title} ({self.created_at})"

    class Meta:
        verbose_name_plural = "Knowledge Store"
