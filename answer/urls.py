# answer/api_urls.py
from django.urls import path
from . import api_views
from . import views

urlpatterns = [
    path('autosave-answer/', views.autosave_answer, name='autosave_answer'),
    path('<int:exam_id>/', views.exam_detail, name='exam_detail'),
    path('<int:exam_id>/join/', views.join_exam_code, name='join_exam_code'),
    path('<int:exam_id>/start_exam/', views.start_exam, name='start_exam'),
    path('do/<int:student_exam_id>/', views.do_exam, name='do_exam'),
    path('submit/<int:student_exam_id>/', views.submit_exam, name='submit_exam'),
    path('result/<int:student_exam_id>/', views.exam_result, name='exam_result'),
    path('continue/<int:student_exam_id>/', views.exam_continue, name='exam_continue'),
]
