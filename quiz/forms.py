from django import forms

class ManualQuestionForm(forms.Form):
    question = forms.CharField(widget=forms.Textarea(attrs={'rows': 3, 'class': 'form-control', 'placeholder': 'Enter your question here...'}))
    
    option1 = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Option 1'}))
    option2 = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Option 2'}))
    option3 = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Option 3'}))
    option4 = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Option 4'}))
    
    correct_option = forms.ChoiceField(
        choices=[
            ("1", "Option 1"),
            ("2", "Option 2"),
            ("3", "Option 3"),
            ("4", "Option 4")
        ],
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    explanation = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 2, 'class': 'form-control', 'placeholder': 'Optional: Explain why the correct answer is right...'}),
        required=False
    )
