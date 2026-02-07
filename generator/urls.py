from django.urls import path
from . import views

app_name = 'generator'

urlpatterns = [
    path('generate/', views.study_plan, name='study_plan'),
    path('unit/<int:unit_id>/', views.generate_unit_plan, name='generate_unit_plan'),
]
