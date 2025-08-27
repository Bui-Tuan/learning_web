from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout, update_session_auth_hash
from .forms import UserRegisterForm, ProfileUpdateForm
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from .decorators import anonymous_required, role_required
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required


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
    return render(request, 'accounts/teacher_dashboard.html', {'user': request.user})


@role_required('student')
def student_dashboard(request):
    return render(request, 'accounts/student_dashboard.html', {'user': request.user})


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