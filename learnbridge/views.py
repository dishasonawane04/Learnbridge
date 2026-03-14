from django.shortcuts import render
from django.contrib.auth.decorators import login_required

def dashboard(request):
    """
    Main Entry Point for LearnBridge.
    Links to all sub-applications.
    """
    apps = [
        {
            "name": "AI Tutor",
            "desc": "24/7 Personal Tutor for any topic.",
            "url": "/ai-tutor/",
            "icon": "ph-robot",
            "color": "#4a90e2"
        },
        {
            "name": "Quiz Master",
            "desc": "Test your knowledge with quizzes.",
            "url": "/quiz/",
            "icon": "ph-check-circle",
            "color": "#f59e0b"
        },
        {
            "name": "Learning Support",
            "desc": "Get hints and simple explanations.",
            "url": "/support/",
            "icon": "ph-life-buoy",
            "color": "#10b981"
        },
        {
            "name": "Flashcards",
            "desc": "Generate flashcards from notes.",
            "url": "/flashcards/",
            "icon": "ph-cards",
            "color": "#8b5cf6"
        },
        {
            "name": "Assessment",
            "desc": "Upload assignments for grading.",
            "url": "/assessment/",
            "icon": "ph-clipboard-text",
            "color": "#ec4899"
        },
        {
            "name": "LOR Generator",
            "desc": "Create professional academic letters.",
            "url": "/lor/",
            "icon": "ph-scroll",
            "color": "#6366f1",
            "role": "Teacher"  # Only visible to Teachers
        },
        {
            "name": "Analytics",
            "desc": "Track your progress and performance.",
            "url": "/analytics/dashboard/",
            "icon": "ph-chart-bar",
            "color": "#f59e0b"
        },
        {
            "name": "Prerequisite Checker",
            "desc": "Check your readiness for advanced topics.",
            "url": "/check-readiness/",
            "icon": "ph-check-square-offset",
            "color": "#6366f1"
        }
    ]

    # Filter apps based on role
    visible_apps = []
    user_role = 'Student' # Default
    
    if request.user.is_authenticated:
        try:
            # Try accounts profile first
            if hasattr(request.user, 'account_profile'):
                user_role = request.user.account_profile.role
            elif hasattr(request.user, 'core_profile'):
                # Fallback to core profile if it has role, though core profile role field might be different
                 user_role = request.user.core_profile.role.capitalize() # core uses 'student'/'teacher' lowercase
            print(f"DEBUG: User {request.user.username} has role: {user_role}")
        except Exception as e:
            print(f"DEBUG: Error getting profile for {request.user.username}: {e}")
            pass # Keep as Student/Default if no profile

    for app in apps:
        allowed_role = app.get('role')
        
        # Default: Show app
        show_app = True
        
        # Rule 1: If app is Teacher-only, hide from non-teachers
        if allowed_role == 'Teacher' and user_role != 'Teacher':
            show_app = False
            
        # Rule 2: If app is Student-only (if we had any), hide from Teachers? 
        # (Requirement says Teachers access everything, so no hiding for Teachers)
        
        if show_app:
            visible_apps.append(app)

    return render(request, "dashboard.html", {"apps": visible_apps, "user_role": user_role})
