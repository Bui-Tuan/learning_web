# exam/urls.py
from . import views
from django.urls import path

urlpatterns = [
    # Tạo đề cho lớp cụ thể
    path('classroom/<int:classroom_id>/create/', views.create_exam, name='create_exam_for_classroom'),
    # Tạo đề chung (chọn lớp trong form)
    path('create/', views.create_exam, name='create_exam'),
    path('create-from-uploaded/', views.create_exam_from_uploaded, name='create_exam_from_uploaded'),
    path('list/', views.exam_list, name='exam_list'),
    path('classroom/<int:classroom_id>/list/', views.exam_list, name='exam_list_by_classroom'),
    path('<int:exam_id>/edit/', views.exam_edit, name='exam_edit'),
    path('<int:exam_id>/delete/', views.exam_delete, name='exam_delete'),
    path('student/', views.student_exams, name='student_exams'),
]
