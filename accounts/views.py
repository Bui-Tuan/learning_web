from django.shortcuts import render, redirect
from django.utils import timezone
from django.contrib.auth import login, authenticate, logout, update_session_auth_hash
from .forms import UserRegisterForm, ProfileUpdateForm
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from .decorators import anonymous_required, role_required
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from classroom.models import Classroom
from answer.models import StudentExam
from exam.models import Exam
from question.models import Question
from .utils import _get_exam_end, _get_exam_start, _get_studentexam_score, _get_studentexam_submitted_at, _model_has_field
from django.db.models import Q, Avg


# Create your views here.


@anonymous_required
def register_view(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)  # Đăng nhập ngay sau khi đăng ký
            return redirect('dashboard')  # Hoặc redirect tới trang dashboard
    else:
        form = UserRegisterForm()
    return render(request, 'accounts/register.html', {'form': form})


@anonymous_required
def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('dashboard')
    else:
        form = AuthenticationForm()
    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('login')


@login_required
def dashboard_view(request):
    user = request.user
    if user.is_superuser:
        return redirect('admin_dashboard')  # dành cho admin Django
    elif user.role == 'teacher':
        return redirect('teacher_dashboard')
    elif user.role == 'student':
        return redirect('student_dashboard')
    else:
        return redirect('home')  # fallback nếu role không hợp lệ


@role_required('teacher')
def teacher_dashboard(request):
    stats = {
        "classroom_count": Classroom.objects.filter(id_teacher=request.user).count(),
        "question_count": Question.objects.filter(owner=request.user).count(),
        "exam_count": Exam.objects.filter(created_by=request.user).count() if hasattr(Exam,'created_by') else Exam.objects.count(),
        "submission_week": 0,  # TODO: fill bằng query StudentExam nếu có
    }
    classrooms = Classroom.objects.filter(id_teacher=request.user).order_by('-id')[:8]
    upcoming_exams = Exam.objects.order_by('start_time')[:6] if hasattr(Exam,'start_time') else Exam.objects.all()[:6]
    return render(request, "accounts/teacher_dashboard.html", {
        "stats": stats, "classrooms": classrooms, "upcoming_exams": upcoming_exams
    })


@login_required
@role_required('student')
def student_dashboard(request):
    user = request.user
    now = timezone.now()

    # ===== LỚP HỌC ĐÃ THAM GIA =====
    # Lấy id các lớp mà học sinh thuộc về
    class_ids = list(
        Classroom.objects.filter(students__id_student=user).values_list('id', flat=True).distinct()
    )
    class_count = len(class_ids)

    # ===== KỲ THI SẮP TỚI =====
    # Lấy các đề thuộc các lớp trên (giới hạn một chút rồi lọc/sắp xếp ở python cho linh hoạt)
    exams_qs = Exam.objects.filter(classroom_id__in=class_ids).order_by('-id')[:100]
    exams = list(exams_qs)

    upcoming = []
    for e in exams:
        st = _get_exam_start(e)
        et = _get_exam_end(e)
        # Điều kiện "sắp tới/mở": (chưa bắt đầu nhưng sắp đến) hoặc (đang mở)
        if st and st >= now:
            upcoming.append((st, e))
        elif st and et and st <= now <= et:
            upcoming.append((st, e))
        elif not st and et and et >= now:
            upcoming.append((et, e))  # không có start, nhưng còn hạn -> tạm xem là sắp/đang diễn ra
    # sắp xếp theo thời điểm gần nhất
    upcoming.sort(key=lambda x: (x[0] or now))
    upcoming_exams = [e for _, e in upcoming][:6]

    # ===== KẾT QUẢ GẦN ĐÂY =====
    se_qs = StudentExam.objects.filter(student=user)
    # ưu tiên bản ghi đã "submitted"
    if _model_has_field(StudentExam, 'status'):
        se_qs = se_qs.order_by('-id')
        submitted_qs = se_qs.filter(status='submitted')
    else:
        submitted_qs = se_qs

    # sắp theo thời gian nộp (nếu có)
    recent = list(submitted_qs[:100])
    recent.sort(key=lambda se: (_get_studentexam_submitted_at(se) or timezone.datetime(1970,1,1, tzinfo=timezone.utc)), reverse=True)
    recent_results = recent[:6]

    # ===== THỐNG KÊ NHANH =====
    submitted_count = submitted_qs.count()
    avg_score = None
    if _model_has_field(StudentExam, 'score'):
        avg = submitted_qs.aggregate(x=Avg('score'))['x']
        if avg is not None:
            # làm tròn 1 chữ số thập phân
            avg_score = round(avg, 1)
    elif _model_has_field(StudentExam, 'mark'):
        avg = submitted_qs.aggregate(x=Avg('mark'))['x']
        if avg is not None:
            avg_score = round(avg, 1)

    stats = {
        "class_count": class_count,
        "upcoming_exams": len(upcoming_exams),
        "submitted": submitted_count,
        "avg_score": avg_score if avg_score is not None else "—",
    }

    return render(request, "dashboard_base_student.html", {
        "stats": stats,
        "upcoming_exams": upcoming_exams,
        "recent_results": recent_results,
    })


@staff_member_required
def admin_dashboard(request):
    return render(request, 'accounts/admin_dashboard.html', {'user': request.user})


@login_required
def profile_view(request):
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            return redirect('profile')
    else:
        form = ProfileUpdateForm(instance=request.user)

    return render(request, 'accounts/profile.html', {'form': form})


@login_required
def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # để người dùng không bị đăng xuất
            return redirect('profile')
    else:
        form = PasswordChangeForm(user=request.user)

    return render(request, 'accounts/change_password.html', {'form': form})


def demo(request):
    return render(request, 'dashboard_base_student.html')