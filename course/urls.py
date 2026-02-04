from django.urls import path
from . import views

app_name = 'course'

urlpatterns = [
    path('', views.course_list, name='list'),
    path('create/', views.course_create, name='create'),
    path('<int:course_id>/', views.course_detail, name='detail'),
    path('unit/<int:unit_id>/', views.unit_detail, name='unit_detail'),
    path('<int:course_id>/unit/add/', views.unit_add, name='unit_add'),
    path('unit/<int:unit_id>/upload/', views.material_upload, name='material_upload'),
]
