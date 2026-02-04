from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User

class FlashcardDeck(models.Model):
    title = models.CharField(max_length=200)
    unit = models.ForeignKey('course.CourseUnit', on_delete=models.SET_NULL, null=True, blank=True, related_name='flashcard_decks')
    created_at = models.DateTimeField(default=timezone.now)
    difficulty = models.CharField(max_length=20, default="Medium")
    
    def __str__(self):
        return self.title
    
    @property
    def total_cards(self):
        return self.cards.count()
    
    @property
    def mastery_percentage(self):
        total = self.cards.count()
        if total == 0: return 0
        known = self.cards.filter(box__gt=1).count() # Leitner system box > 1
        return int((known / total) * 100)

class Flashcard(models.Model):
    DIFFICULTY_CHOICES = [
        ('Easy', 'Easy'),
        ('Medium', 'Medium'),
        ('Hard', 'Hard')
    ]
    
    TYPE_CHOICES = [
        ('QA', 'Question & Answer'),
        ('Definition', 'Definition'),
        ('Example', 'Example'),
        ('MCQ', 'Multiple Choice')
    ]

    deck = models.ForeignKey(FlashcardDeck, on_delete=models.CASCADE, related_name='cards')
    front = models.TextField(help_text="Question or Term")
    back = models.TextField(help_text="Answer or Definition")
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES, default='Medium')
    card_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='QA')
    explanation = models.TextField(blank=True, null=True, help_text="Extra explanation or hint")
    exam_tip = models.TextField(blank=True, null=True, help_text="Exam-focused tip")
    
    # Adaptive / SRS Fields (Leitner System simplified)
    # Box 1: Every day, Box 2: Every 3 days, etc.
    box = models.IntegerField(default=1) 
    next_review_date = models.DateTimeField(default=timezone.now)
    last_reviewed_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.front[:30]}..."

    def move_forward(self):
        self.box += 1
        self.last_reviewed_at = timezone.now()
        # Simple spacing: 1, 3, 7, 14, 30 days
        days = [1, 3, 7, 14, 30]
        interval = days[min(self.box, len(days)-1)]
        self.next_review_date = timezone.now() + timezone.timedelta(days=interval)
        self.save()

    def reset_progress(self):
        self.box = 1
        self.last_reviewed_at = timezone.now()
        self.next_review_date = timezone.now() # Review ASAP
        self.save()
