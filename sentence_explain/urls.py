from django.urls import path
from . import views

urlpatterns = [
    path('', views.sentence_explain, name='sentence_explain'),
]
