"""
URL configuration for learnbridge project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from . import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('ai/', include('ai_tutor.urls')),
    path('support/', include('learning_support.urls')),
    path('flashcards/', include('flashcard_generator.urls')),
    path('quiz/', include('quiz.urls')),
    path('assessment/', include('assessment.urls')),
    path('lor/', include('letter_of_recommendation_generator.urls', namespace='letter_of_recommendation_generator')),
    path('analytics/', include('analytics.urls')),
    path('check-readiness/', include('prerequisite_checker.urls', namespace='prerequisite_checker')),
    path('accounts/', include('accounts.urls')),
    path('', views.dashboard, name='dashboard'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
