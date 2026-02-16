from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('dashboard/teacher/', views.teacher_dashboard, name='teacher_dashboard'),
    path('dashboard/student/', views.student_dashboard, name='student_dashboard'),
    path('dashboard/admin/', views.admin_dashboard, name='admin_dashboard'),
    path('profile/', views.profile_view, name='profile'),
    path('change-password/', views.change_password, name='change_password'),
    path('demo/', views.demo, name='demo'),
]
