from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Classroom, ClassroomStudent
from .forms import ClassroomForm, JoinClassroomForm
from django.http import HttpResponseForbidden
from .decorators import role_required
from django.contrib import messages
from django.urls import reverse


@login_required
def classroom_list(request):
    user = request.user

    if user.role == 'teacher':
        # Lấy các lớp mà giáo viên đó quản lý
        classrooms = Classroom.objects.filter(id_teacher=user)
        return render(request, 'classroom/classes_list_teacher.html', {'classrooms': classrooms})

    elif user.role == 'student':
        # Lấy các lớp mà học sinh đã tham gia
        classrooms = Classroom.objects.filter(students__id_student=user).distinct()
        return render(request, 'classroom/classes_list_student.html', {'classrooms': classrooms})


@login_required
@role_required('teacher')
def create_classroom(request):
    if request.method == 'POST':
        form = ClassroomForm(request.POST)
        if form.is_valid():
            classroom = form.save(commit=False)
            classroom.id_teacher = request.user
            classroom.save()
            return redirect('classroom_list')
    else:
        form = ClassroomForm()
    return render(request, 'classroom/classroom_form.html', {'form': form})


@login_required
@role_required('student')
def join_classroom_confirm(request, class_id):
    classroom = get_object_or_404(Classroom, id=class_id)

    if request.method == 'POST':
        form = JoinClassroomForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data['code']
            if code == classroom.code:
                # Kiểm tra đã tham gia chưa
                if not ClassroomStudent.objects.filter(id_classroom=classroom, id_student=request.user).exists():
                    ClassroomStudent.objects.create(id_classroom=classroom, id_student=request.user)
                    messages.success(request, "Bạn đã tham gia lớp học thành công.")
                else:
                    messages.info(request, "Bạn đã ở trong lớp học này.")
                return redirect('classroom_detail', class_id=classroom.id)
            else:
                messages.error(request, "Mã lớp không đúng.")
    else:
        form = JoinClassroomForm()

    return render(request, 'classroom/join_classroom_confirm.html', {
        'form': form,
        'classroom': classroom
    })


@login_required
@role_required('student')
def available_classes_for_student(request):
    # Lấy danh sách tất cả các lớp đang mở
    classrooms = Classroom.objects.filter(status='open')

    return render(request, 'classroom/available_classes.html', {
        'classrooms': classrooms
    })


@login_required
def classroom_detail(request, class_id):
    classroom = get_object_or_404(Classroom, id=class_id)
    user = request.user

    already_joined = ClassroomStudent.objects.filter(
        id_classroom=classroom,
        id_student=user
    ).exists()

    context = {
        'classroom': classroom,
        'already_joined': already_joined,
    }

    return render(request, 'classroom/classroom_detail.html', context)


@login_required
@role_required('teacher')
def modify_classroom(request, class_id):
    classroom = get_object_or_404(Classroom, id=class_id)

    if request.method == 'POST':
        form = ClassroomForm(request.POST, instance=classroom)
        if form.is_valid():
            form.save()
            messages.success(request, 'Đã cập nhật lớp học thành công.')
            return redirect('classroom_detail', class_id=class_id)
    else:
        form = ClassroomForm(instance=classroom)

    return render(request, 'classroom/modify_classroom.html', {'form': form, 'classroom': classroom})


@login_required
@role_required('teacher')
def delete_classroom(request, class_id):
    classroom = get_object_or_404(Classroom, id=class_id)
    if request.method == "POST":
        classroom.delete()
        messages.success(request, "Classroom has been deleted successfully.")
        return redirect(reverse('classroom_list'))  # Điều hướng về danh sách classroom
    return redirect(reverse('classroom_detail', args=[class_id]))


@login_required
@role_required('teacher')
def student_list_in_class(request, class_id):
    classroom = get_object_or_404(Classroom, id=class_id)

    students = ClassroomStudent.objects.filter(id_classroom=classroom).select_related('id_student')

    return render(request, 'classroom/student_list_in_class.html', {
        'classroom': classroom,
        'students': students,
    })