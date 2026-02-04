from django.urls import path
from . import views

urlpatterns = [
    path('generate/', views.study_plan, name='study_plan'),
]
