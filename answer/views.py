# answer/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.contrib import messages
from classroom.models import ClassroomStudent
from .models import Exam, StudentExam, StudentAnswer
from .decorators import role_required
from django import forms
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse


@login_required
@role_required('student')
def exam_detail(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id)
    user = request.user

    # Kiểm tra học sinh đã vào lớp chưa
    in_class = ClassroomStudent.objects.filter(id_classroom=exam.classroom, id_student=user).exists()
    if not in_class:
        return render(request, 'answer/not_in_class.html', {'answer': exam})

    now = timezone.now()
    if not (exam.open_time <= now <= exam.close_time):
        return render(request, 'answer/not_available.html', {'answer': exam})

    # Tìm số lần làm bài của học sinh cho answer này
    attempts = StudentExam.objects.filter(student=user, exam=exam).order_by('-attempt_number')
    current_attempt = attempts.first()
    remaining_attempts = exam.max_attempts - attempts.count()

    return render(request, 'answer/exam_detail.html', {
        'exam': exam,
        'remaining_attempts': remaining_attempts,
        'current_attempt': current_attempt,
    })


class JoinExamCodeForm(forms.Form):
    code = forms.CharField(label="Nhập mã bài kiểm tra", max_length=8)


@login_required
@role_required('student')
def join_exam_code(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id)
    user = request.user

    # Chỉ học sinh đã ở trong lớp mới join
    in_class = ClassroomStudent.objects.filter(id_classroom=exam.classroom, id_student=user).exists()
    if not in_class:
        return redirect('exam_detail', exam_id=exam.id)

    # Đã tham gia (ít nhất 1 lần), không cho nhập lại code
    if StudentExam.objects.filter(student=user, exam=exam).exists():
        return redirect('exam_detail', exam_id=exam.id)

    form = JoinExamCodeForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        if form.cleaned_data['code'].upper() == exam.code:
            # Tạo bản ghi StudentExam (lần thử đầu tiên)
            StudentExam.objects.create(
                student=user,
                exam=exam,
                status='joined',
                attempt_number=1
            )
            messages.success(request, "Đã tham gia bài kiểm tra.")
            return redirect('exam_detail', exam_id=exam.id)
        else:
            messages.error(request, "Mã bài kiểm tra không đúng!")

    return render(request, 'answer/join_exam_code.html', {'exam': exam, 'form': form})


@login_required
@role_required('student')
def start_exam(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id)
    user = request.user

    has_unlocked = StudentExam.objects.filter(student=user, exam=exam).exists()
    if not has_unlocked:
        # Nếu chưa unlock, bắt nhập code
        return redirect('join_exam_code', exam_id=exam.id)

    current_attempts = StudentExam.objects.filter(student=user, exam=exam).count()
    if current_attempts >= exam.max_attempts:
        messages.error(request, "Bạn đã hết số lượt làm bài.")
        return redirect('exam_detail', exam_id=exam.id)

    last_exam = StudentExam.objects.filter(student=user, exam=exam).order_by('-attempt_number').first()
    if last_exam.status == 'joined':
        last_exam.start_exam()
        return redirect('do_exam', student_exam_id=last_exam.id)
    elif last_exam.status == 'submitted':
        student_exam = StudentExam.objects.create(
            student=user,
            exam=exam,
            attempt_number=(last_exam.attempt_number + 1),
            status='joined'
        )
        student_exam.start_exam()
        return redirect('do_exam', student_exam_id=student_exam.id)
    else:
        return redirect('exam_continue', exam.id)


@login_required
@role_required('student')
def do_exam(request, student_exam_id):
    student_exam = get_object_or_404(StudentExam, id=student_exam_id, student=request.user)
    exam = student_exam.exam

    now = timezone.now()
    if student_exam.status != 'in_process':
        return redirect('exam_detail', exam_id=exam.id)

    start_time = student_exam.start_at
    end_time = start_time + timezone.timedelta(minutes=exam.duration_minutes)
    remaining_seconds = int((end_time - now).total_seconds())
    if remaining_seconds <= 0:
        # Nếu đã hết giờ, tự nộp bài
        student_exam.submit_exam()
        return redirect('exam_result', student_exam_id=student_exam.id)

    exam_questions = exam.questions.select_related('question').order_by('position')
    question_data = []
    for eq in exam_questions:
        q = eq.question
        choices = q.choices.order_by('label')
        question_data.append({
            'id': q.id,
            'content': q.content,
            'choices': [{'label': c.label, 'text': c.text} for c in choices],
        })

    try:
        student_answer = StudentAnswer.objects.get(student_exam=student_exam)
        answers = student_answer.answers or {}
    except StudentAnswer.DoesNotExist:
        answers = {}

    context = {
        'student_exam': student_exam,
        'exam': exam,
        'questions': question_data,
        'answers': answers,
        'remaining_seconds': remaining_seconds,
        'now': timezone.now(),
    }
    return render(request, 'answer/do_exam.html', context)


@login_required
@csrf_exempt
def autosave_answer(request):
    if request.method == "POST":
        student_exam_id = request.POST.get('student_exam_id')
        student_exam = get_object_or_404(StudentExam, id=student_exam_id, student=request.user)
        # Lấy tất cả đáp án
        answers = {}
        for key, value in request.POST.items():
            if key.startswith('answer_'):
                qid = key.replace('answer_', '')
                answers[qid] = value
        # Lưu hoặc update đáp án
        obj, _ = StudentAnswer.objects.get_or_create(student_exam=student_exam)
        obj.answers = answers
        obj.save()
        return JsonResponse({'status': 'ok'})
    return JsonResponse({'status': 'fail'}, status=400)


@login_required
@role_required('student')
def submit_exam(request, student_exam_id):
    student_exam = get_object_or_404(StudentExam, id=student_exam_id, student=request.user)
    if student_exam.status == 'submitted':
        return redirect('exam_result', student_exam_id=student_exam.id)
    if request.method == "POST":
        # Lấy đáp án gửi lên (có thể gửi lại từ autosave/localStorage)
        answers = {}
        for key, value in request.POST.items():
            if key.startswith('answer_'):
                qid = key.replace('answer_', '')
                answers[qid] = value

        # Lưu hoặc update đáp án
        student_answer, _ = StudentAnswer.objects.get_or_create(student_exam=student_exam)
        student_answer.answers = answers
        student_answer.save()

        # Đánh dấu nộp bài, ghi thời gian
        student_exam.status = 'submitted'
        student_exam.submit_at = timezone.now()
        student_exam.save(update_fields=['status', 'submit_at'])

        # Gọi hàm chấm điểm tự động nếu có
        if hasattr(student_answer, 'auto_score'):
            student_answer.auto_score()  # bạn định nghĩa hàm này trong model
        return JsonResponse({'status': 'ok', 'redirect': True})
    return redirect('exam_result', student_exam_id=student_exam.id)


@login_required
@role_required('student')
def exam_result(request, student_exam_id):
    student_exam = get_object_or_404(StudentExam, id=student_exam_id, student=request.user)
    exam = student_exam.exam
    # Lấy đáp án của học sinh
    try:
        student_answer = StudentAnswer.objects.get(student_exam=student_exam)
        answers = student_answer.answers or {}
        # Nếu bạn có trường score thì lấy luôn
        score = getattr(student_answer, 'score', None)
    except StudentAnswer.DoesNotExist:
        answers = {}
        score = None

    # Tạo data để hiện ra chi tiết: đúng/sai từng câu
    question_results = []
    exam_questions = exam.questions.select_related('question').order_by('position')
    for eq in exam_questions:
        q = eq.question
        correct = q.correct_answer
        student_ans = answers.get(str(q.id))
        question_results.append({
            'content': q.content,
            'choices': list(q.choices.order_by('label')),
            'student_answer': student_ans,
            'correct_answer': correct,
            'is_correct': student_ans == correct,
        })

    context = {
        'exam': exam,
        'student_exam': student_exam,
        'score': score,
        'question_results': question_results,
    }
    return render(request, 'answer/exam_result.html', context)


@login_required
@role_required('student')
def exam_continue(request, student_exam_id):
    student_exam = get_object_or_404(StudentExam, id=student_exam_id, student=request.user)
    exam = student_exam.exam

    # Nếu bài đã nộp hoặc chưa bắt đầu thì không cho tiếp tục
    if student_exam.status != 'in_process':
        return redirect('exam_result', student_exam_id=student_exam.id)

    # Kiểm tra còn thời gian không
    now = timezone.now()
    start_time = student_exam.start_at
    end_time = start_time + timezone.timedelta(minutes=exam.duration_minutes)
    remaining_seconds = int((end_time - now).total_seconds())

    if remaining_seconds <= 0:
        # Hết giờ, tự động nộp bài và chuyển sang trang kết quả
        student_exam.status = 'submitted'
        student_exam.submit_at = now
        student_exam.save(update_fields=['status', 'submit_at'])
        # Gọi hàm chấm điểm nếu có
        return redirect('exam_result', student_exam_id=student_exam.id)

    # Nếu vẫn còn thời gian, chuyển sang trang làm bài (giống như vào mới)
    return redirect('do_exam', student_exam_id=student_exam.id)