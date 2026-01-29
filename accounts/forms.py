from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import UserProfile

class SignupForm(UserCreationForm):
    full_name = forms.CharField(max_length=255, required=True, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Full Name'}))
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email Address'}))
    role = forms.ChoiceField(choices=UserProfile.ROLE_CHOICES, widget=forms.Select(attrs={'class': 'form-select'}))

    class Meta:
        model = User
        fields = ('full_name', 'email', 'username', 'role')

    def __init__(self, *args, **kwargs):
        super(SignupForm, self).__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'
            field.widget.attrs['placeholder'] = field.label
        
        # Specific tweaks
        self.fields['role'].widget.attrs['class'] = 'form-select'

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("This email is already registered.")
        return email

class LoginForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'}))

class ForgotPasswordForm(forms.Form):
    email = forms.EmailField(
        label="Enter your registered email",
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email Address'})
    )
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if not User.objects.filter(email=email).exists():
            raise forms.ValidationError("No account found with this email address.")
        return email

class OTPVerificationForm(forms.Form):
    otp = forms.CharField(
        label="Enter 6-digit OTP",
        max_length=6,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '123456', 'type': 'tel'})
    )

class ResetPasswordForm(forms.Form):
    new_password = forms.CharField(
        label="New Password",
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'New Password'})
    )
    confirm_password = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm Password'})
    )

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("new_password")
        confirm_password = cleaned_data.get("confirm_password")

        if password != confirm_password:
            raise forms.ValidationError("Passwords do not match.")
        return cleaned_data
