from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Course, CourseUnit, CourseMaterial
from .utils.extraction import extract_content

@login_required
def course_list(request):
    courses = request.user.courses.all()
    return render(request, 'course/course_list.html', {'courses': courses})

@login_required
def course_create(request):
    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')
        level = request.POST.get('level')
        course = Course.objects.create(
            user=request.user, 
            title=title, 
            description=description, 
            level=level
        )
        return redirect('course_detail', course_id=course.id)
    return render(request, 'course/course_form.html')

@login_required
def course_detail(request, course_id):
    course = get_object_or_404(Course, id=course_id, user=request.user)
    return render(request, 'course/course_detail.html', {'course': course})

@login_required
def unit_add(request, course_id):
    course = get_object_or_404(Course, id=course_id, user=request.user)
    if request.method == 'POST':
        title = request.POST.get('title')
        order = request.POST.get('order', 0)
        CourseUnit.objects.create(course=course, title=title, order=order)
        return redirect('course_detail', course_id=course.id)
    return redirect('course_detail', course_id=course.id)

@login_required
def material_upload(request, unit_id):
    unit = get_object_or_404(CourseUnit, id=unit_id, course__user=request.user)
    if request.method == 'POST' and request.FILES.get('file'):
        material = CourseMaterial.objects.create(
            unit=unit,
            file=request.FILES['file']
        )
        # Process file automatically
        extract_content(material)
        return redirect('course_detail', course_id=unit.course.id)
    return redirect('course_detail', course_id=unit.course.id)
