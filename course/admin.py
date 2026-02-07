from django.contrib import admin
from .models import Course, CourseUnit, CourseMaterial

class CourseUnitInline(admin.TabularInline):
    model = CourseUnit
    extra = 1

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('title', 'level', 'user', 'created_at')
    list_filter = ('level', 'created_at')
    search_fields = ('title', 'description', 'user__username')
    inlines = [CourseUnitInline]

@admin.register(CourseUnit)
class CourseUnitAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'order', 'created_at')
    list_filter = ('course',)
    search_fields = ('title', 'course__title')

@admin.register(CourseMaterial)
class CourseMaterialAdmin(admin.ModelAdmin):
    list_display = ('unit', 'file_type', 'created_at')
    list_filter = ('file_type',)
