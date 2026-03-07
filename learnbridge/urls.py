from django.contrib import admin
from django.urls import path, include
from core import views as core_views
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect

urlpatterns = [
    path('admin/', admin.site.urls),
    path('ai-tutor/', include('ai_tutor.urls', namespace='ai_tutor')),
    path('support/', include('learning_support.urls', namespace='learning_support')),
    path('flashcards/', include('flashcard_generator.urls', namespace='flashcard_generator')),
    path('quiz/', include('quiz.urls', namespace='quiz')),
    path('assessment/', include('assessment.urls', namespace='assessment')),
    path('lor/', include('letter_of_recommendation_generator.urls', namespace='letter_of_recommendation_generator')),
    path('analytics/', include('analytics.urls', namespace='analytics')),
    path('readiness/', include('prerequisite_checker.urls', namespace='prerequisite_checker')),
    path('accounts/', include('accounts.urls', namespace='accounts')),
    path('core/', include('core.urls', namespace='core')),
    path('plan/', include('generator.urls', namespace='generator')),
    path('sentence-explain/', include('sentence_explain.urls', namespace='sentence_explain')),
    path('notes/', include('notes.urls', namespace='notes')),
    path('course/', include('course.urls', namespace='course')),
    path('', core_views.home, name='home'),
    path('login/', lambda r: redirect('accounts:login')),
    path('signup/', lambda r: redirect('accounts:signup')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
