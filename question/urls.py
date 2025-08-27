# question/urls.py
from . import views
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('create/', views.create_question, name='create_question'),
    path('', views.question_list, name='question_list'),
    path('questions/<int:question_id>/edit/', views.edit_question, name='edit_question'),
    # Xóa câu hỏi
    path('delete/<int:question_id>/', views.delete_question, name='delete_question'),
    # Upload file DOCX ngân hàng câu hỏi
    path('upload/', views.upload_file, name='upload_file'),
    # Lưu hàng loạt từ file upload (batch save)
    path('save/', views.save_questions, name='save_questions'),
    # ...
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
