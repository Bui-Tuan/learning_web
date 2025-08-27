from django.urls import path
from . import views

urlpatterns = [
    path('classroom_list/', views.classroom_list, name='classroom_list'),
    path('create/', views.create_classroom, name='create_classroom'),
    # path('delete/', views.register_view, name='register'),
    # path('view/', views.list_class, name='register'),
    # path('join_class/', views.join_class_by_id, name='join_class'),
    # path('modify/', views.register_view, name='register'),
    path('available/', views.available_classes_for_student, name='available_classes'),
    path('<int:class_id>/', views.classroom_detail, name='classroom_detail'),
    path('join/<int:class_id>/', views.join_classroom_confirm, name='join_classroom_confirm'),
    path('<int:class_id>/edit/', views.modify_classroom, name='modify_classroom'),
    path('<int:class_id>/delete/', views.delete_classroom, name='delete_classroom'),
    path('<int:class_id>/students/', views.student_list_in_class, name='student_list_in_class'),
]
