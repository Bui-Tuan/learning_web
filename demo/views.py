from django.shortcuts import render


def public_home(request):
    return render(request, 'public/index.html', {"title": "EduExam – Nền tảng học & kiểm tra trực tuyến"})
