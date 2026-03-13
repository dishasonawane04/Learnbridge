from django.db import models
from django.contrib.auth.models import User
import os

class Note(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notes')
    course = models.ForeignKey('course.Course', on_delete=models.CASCADE, related_name='user_notes', null=True, blank=True)
    topic = models.CharField(max_length=200)
    content = models.TextField()
    is_ai_generated = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f"{self.topic} - {self.user.username}"

class NoteImage(models.Model):
    note = models.ForeignKey(Note, related_name='images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='note_images/')
    extracted_text = models.TextField(blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        if is_new and self.image:
            try:
                from course.utils.extraction import extract_text_from_image
                text = extract_text_from_image(self.image.path)
                if text:
                    NoteImage.objects.filter(pk=self.pk).update(extracted_text=text)
            except Exception as e:
                print(f"OCR Failed for NoteImage {self.id}: {e}")

from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=Note)
def trigger_concept_map_update(sender, instance, created, **kwargs):
    """Triggers concept map generation when a note is saved."""
    if instance.course:
        try:
            from course.services.concept_map import ConceptMapService
            ConceptMapService.generate_for_note(instance.id)
        except Exception as e:
            print(f"Failed to trigger concept map update: {e}")
