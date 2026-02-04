from django import forms
from .models import LetterRequest

class LetterRequestForm(forms.ModelForm):
    class Meta:
        model = LetterRequest
        fields = [
            'student_name', 'course_degree', 'institution_name', 'duration_of_association',
            'academic_performance', 'technical_skills', 'soft_skills', 'achievements',
            'purpose', 'tone'
        ]
        widgets = {
            'student_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter full name'}),
            'course_degree': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., B.Tech Computer Science'}),
            'institution_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'University/College Name'}),
            'duration_of_association': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 2021-2025'}),
            'academic_performance': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Describe grades, rank, key subject performance...'}),
            'technical_skills': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'List technical skills, tools, languages...'}),
            'soft_skills': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Describe leadership, teamwork, communication...'}),
            'achievements': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Projects, internships, hackathons, publications...'}),
            'purpose': forms.Select(attrs={'class': 'form-select'}),
            'tone': forms.Select(attrs={'class': 'form-select'}),
        }
