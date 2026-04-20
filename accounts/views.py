from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.models import User
from django.contrib import messages
from .forms import SignupForm, LoginForm, ForgotPasswordForm, OTPVerificationForm, ResetPasswordForm
from .models import UserProfile
import random
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
import datetime

# ... existing views ...

def forgot_password_view(request):
    if request.method == 'POST':
        form = ForgotPasswordForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            otp = str(random.randint(100000, 999999))
            expiry = timezone.now() + datetime.timedelta(minutes=10)
            
            # Store in session
            request.session['reset_email'] = email
            request.session['reset_otp'] = otp
            request.session['reset_otp_expiry'] = expiry.isoformat()
            
            # Send Email
            send_mail(
                'Password Reset OTP - LearnBridge',
                f'Your One-Time Password for password reset is: {otp}\n\nThis code expires in 10 minutes.',
                settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=False,
            )
            messages.success(request, f"OTP sent to {email}")
            return redirect('accounts:verify_otp')
    else:
        form = ForgotPasswordForm()
    return render(request, 'accounts/forgot_password.html', {'form': form})

def verify_otp_view(request):
    if 'reset_email' not in request.session:
        messages.error(request, "Session expired. Please start over.")
        return redirect('accounts:forgot_password')
    
    if request.method == 'POST':
        form = OTPVerificationForm(request.POST)
        if form.is_valid():
            user_otp = form.cleaned_data['otp']
            session_otp = request.session.get('reset_otp')
            expiry_str = request.session.get('reset_otp_expiry')
            
            current_time = timezone.now()
            expiry_time = datetime.datetime.fromisoformat(expiry_str)

            if user_otp == session_otp and current_time < expiry_time:
                request.session['reset_verified'] = True
                messages.success(request, "OTP Verified.")
                return redirect('accounts:reset_password')
            else:
                messages.error(request, "Invalid or expired OTP.")
    else:
        form = OTPVerificationForm()
    return render(request, 'accounts/verify_otp.html', {'form': form})

def reset_password_view(request):
    if not request.session.get('reset_verified'):
        messages.error(request, "Unauthorized access. Verify OTP first.")
        return redirect('accounts:forgot_password')
    
    if request.method == 'POST':
        form = ResetPasswordForm(request.POST)
        if form.is_valid():
            email = request.session.get('reset_email')
            user = User.objects.get(email=email)
            user.set_password(form.cleaned_data['new_password'])
            user.save()
            
            # Clean up session
            del request.session['reset_email']
            del request.session['reset_otp']
            del request.session['reset_otp_expiry']
            del request.session['reset_verified']
            
            messages.success(request, "Password reset successful! Please login.")
            return redirect('accounts:login')
    else:
        form = ResetPasswordForm()
    return render(request, 'accounts/reset_password.html', {'form': form})

def signup_view(request):
    """
    Handles user registration and role assignment.
    """
    if request.method == 'POST':
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            role = form.cleaned_data.get('role')
            
            # Update the profile via the cached relationship to prevent login signals from overwriting it!
            if hasattr(user, 'account_profile') and getattr(user, 'account_profile') is not None:
                profile = user.account_profile
                profile.role = role
                profile.full_name = form.cleaned_data.get('full_name')
                profile.save()
            else:
                UserProfile.objects.update_or_create(
                    user=user, 
                    defaults={
                        'role': role, 
                        'full_name': form.cleaned_data.get('full_name')
                    }
                )
            
            login(request, user)
            messages.success(request, f"Welcome, {user.username}! You signed up as a {role}.")
            return redirect('core:dashboard')
    else:
        form = SignupForm()
    
    return render(request, 'accounts/signup.html', {'form': form})

def login_view(request):
    """
    Handles user login and role-based redirection.
    """
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            
            try:
                profile = user.account_profile
                messages.success(request, f"Welcome back, {profile.full_name} ({profile.role})!")
            except UserProfile.DoesNotExist:
                # Handle fallback if no profile exists (e.g., admin users created via CLI)
                messages.warning(request, "User profile missing. Please update your profile.")
                return redirect('core:dashboard')

            # Role-based redirection can be refined here if needed
            # For now, both roles go to the main dashboard
            return redirect('core:dashboard')
    else:
        form = LoginForm()
            
    return render(request, 'accounts/login.html', {'form': form})

def logout_view(request):
    """
    Logs out the user and redirects to login.
    """
    logout(request)
    messages.info(request, "You have successfully logged out.")
    return redirect('accounts:login')
