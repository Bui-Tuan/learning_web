# exam/views.py
import random, string
from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Count
from django.core.paginator import Paginator
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from question.decorators import role_required  # đã có trong project
from question.models import Question
from classroom.models import Classroom
from exam.models import Exam, ExamQuestion
from answer.models import StudentExam


def _generate_exam_code(length=6):
    # Ví dụ: 6 ký tự in hoa + số, tránh đụng code đang có
    chars = string.ascii_uppercase + string.digits
    for _ in range(30):
        code = ''.join(random.choice(chars) for _ in range(length))
        if not hasattr(Exam, 'objects') or not Exam.objects.filter(code=code).exists():
            return code
    return ''.join(random.choice(chars) for _ in range(length))


class CreateExamFromUploadedForm(forms.Form):
    classroom = forms.ModelChoiceField(
        queryset=Classroom.objects.all(),
        label="Lớp học",
        help_text="Chọn lớp sẽ giao bài."
    )
    title = forms.CharField(label="Tiêu đề đề thi", max_length=255)
    duration = forms.IntegerField(label="Thời lượng (phút)", min_value=1, initial=45)
    start_time = forms.DateTimeField(
        label="Thời gian mở (tuỳ chọn)", required=False,
        widget=forms.DateTimeInput(attrs={"type": "datetime-local"})
    )
    end_time = forms.DateTimeField(
        label="Thời gian đóng (tuỳ chọn)", required=False,
        widget=forms.DateTimeInput(attrs={"type": "datetime-local"})
    )

    def clean(self):
        data = super().clean()
        st, et = data.get("start_time"), data.get("end_time")
        if st and et and et <= st:
            self.add_error("end_time", "Thời gian đóng phải sau thời gian mở.")
        return data


@login_required
@role_required('teacher')
def create_exam_from_uploaded(request):
    """
    Tạo Exam từ các câu hỏi đã upload thành công gần nhất.
    Dựa vào request.session['last_uploaded_question_ids'] (đã được set ở save_questions).
    """
    ids = request.session.get('last_uploaded_question_ids') or []
    if not ids:
        messages.warning(request, "Không tìm thấy danh sách câu hỏi vừa upload trong phiên làm việc.")
        return redirect('question_list')  # hoặc trang phù hợp của bạn

    qs = list(Question.objects.filter(id__in=ids).order_by('-id'))
    if not qs:
        messages.warning(request, "Danh sách ID câu hỏi không hợp lệ hoặc đã bị xoá.")
        return redirect('question_list')

    if request.method == 'POST':
        form = CreateExamFromUploadedForm(request.POST)
        if form.is_valid():
            classroom = form.cleaned_data['classroom']
            title = form.cleaned_data['title']
            duration = form.cleaned_data['duration']
            start_time = form.cleaned_data.get('start_time')
            end_time = form.cleaned_data.get('end_time')

            exam = Exam()

            # Gán lớp học & tiêu đề
            if hasattr(exam, 'classroom'):
                exam.classroom = classroom
            if hasattr(exam, 'title'):
                exam.title = title
            elif hasattr(exam, 'name'):
                exam.name = title

            # Thời lượng: chấp nhận duration_minutes hoặc duration
            if hasattr(exam, 'duration_minutes'):
                exam.duration_minutes = duration
            elif hasattr(exam, 'duration'):
                exam.duration = duration

            # Thời gian mở/đóng: thử các tên field phổ biến
            if start_time:
                for fld in ['start_time', 'open_time', 'start_at', 'available_from']:
                    if hasattr(exam, fld):
                        setattr(exam, fld, start_time)
                        break
            if end_time:
                for fld in ['end_time', 'close_time', 'end_at', 'available_to', 'deadline']:
                    if hasattr(exam, fld):
                        setattr(exam, fld, end_time)
                        break

            # Người tạo (nếu có field)
            for fld in ['created_by', 'creator', 'owner', 'teacher']:
                if hasattr(exam, fld):
                    setattr(exam, fld, request.user)
                    break

            # Code đề (nếu model có field code)
            if hasattr(exam, 'code') and not getattr(exam, 'code', None):
                exam.code = _generate_exam_code(6)

            # Kích hoạt mặc định
            for fld in ['is_active', 'active']:
                if hasattr(exam, fld) and getattr(exam, fld) is None:
                    setattr(exam, fld, True)

            exam.save()

            # Liên kết câu hỏi theo thứ tự
            order = 1
            for q in qs:
                ExamQuestion.objects.create(exam=exam, question=q, order=order)
                order += 1

            # Xoá “danh sách upload gần nhất” để tránh tạo nhầm lần 2
            try:
                del request.session['last_uploaded_question_ids']
            except KeyError:
                pass

            messages.success(request, f"Tạo đề thi “{getattr(exam, 'title', getattr(exam, 'name', ''))}” từ {len(qs)} câu hỏi thành công.")
            # Điều hướng: về chi tiết lớp học hoặc chi tiết đề thi tuỳ bạn đã có URL nào
            try:
                return redirect('classroom_detail', class_id=classroom.id)
            except Exception:
                return redirect('question_list')
    else:
        # Gợi ý tiêu đề mặc định
        default_title = f"Đề từ upload ({len(qs)} câu) - {timezone.localtime().strftime('%d/%m/%Y %H:%M')}"
        form = CreateExamFromUploadedForm(initial={'title': default_title})

    return render(request, 'exam/create_from_uploaded.html', {
        'form': form,
        'uploaded_questions': qs,
    })


class CreateExamForm(forms.Form):
    classroom = forms.ModelChoiceField(
        queryset=Classroom.objects.all(),
        label="Lớp học"
    )
    title = forms.CharField(label="Tiêu đề đề thi", max_length=255)
    duration = forms.IntegerField(label="Thời lượng (phút)", min_value=1, initial=45)
    start_time = forms.DateTimeField(
        label="Thời gian mở (tuỳ chọn)", required=False,
        widget=forms.DateTimeInput(attrs={"type": "datetime-local"})
    )
    end_time = forms.DateTimeField(
        label="Thời gian đóng (tuỳ chọn)", required=False,
        widget=forms.DateTimeInput(attrs={"type": "datetime-local"})
    )

    # Bộ lọc chọn câu hỏi
    q_keyword = forms.CharField(label="Từ khoá", required=False)
    q_rate = forms.ChoiceField(
        label="Độ khó", required=False,
        choices=[("", "— Tất cả —"), ("Dễ", "Dễ"), ("Trung Bình", "Trung Bình"), ("Khó", "Khó")]
    )
    q_subject = forms.CharField(label="Môn", required=False)
    q_grade = forms.CharField(label="Khối", required=False)

    def clean(self):
        data = super().clean()
        st, et = data.get("start_time"), data.get("end_time")
        if st and et and et <= st:
            self.add_error("end_time", "Thời gian đóng phải sau thời gian mở.")
        return data


def _assign_exam_fields(exam: Exam, *, classroom, title, duration, start_time=None, end_time=None, user=None):
    """Gán field theo tên có sẵn trong model Exam (linh hoạt)."""
    if hasattr(exam, 'classroom'):
        exam.classroom = classroom
    # title/name
    if hasattr(exam, 'title'):
        exam.title = title
    elif hasattr(exam, 'name'):
        exam.name = title
    # duration
    if hasattr(exam, 'duration_minutes'):
        exam.duration_minutes = duration
    elif hasattr(exam, 'duration'):
        exam.duration = duration
    # thời gian
    if start_time:
        for fld in ['start_time', 'open_time', 'start_at', 'available_from']:
            if hasattr(exam, fld):
                setattr(exam, fld, start_time); break
    if end_time:
        for fld in ['end_time', 'close_time', 'end_at', 'available_to', 'deadline']:
            if hasattr(exam, fld):
                setattr(exam, fld, end_time); break
    # owner/creator
    for fld in ['created_by', 'creator', 'owner', 'teacher']:
        if hasattr(exam, fld):
            setattr(exam, fld, user); break
    # code
    if hasattr(exam, 'code') and not getattr(exam, 'code', None):
        exam.code = _generate_exam_code(6)
    # active flag
    for fld in ['is_active', 'active']:
        if hasattr(exam, fld) and getattr(exam, fld) is None:
            setattr(exam, fld, True)


@login_required
@role_required('teacher')
def create_exam(request, classroom_id=None):
    """
    Tạo đề thi thủ công: chọn câu hỏi từ ngân hàng của giáo viên.
    - GET: hiển thị form + danh sách câu hỏi theo bộ lọc, có phân trang
    - POST: nhận selected_questions -> tạo Exam + ExamQuestion(order)
    """
    initial = {}
    if classroom_id:
        initial['classroom'] = get_object_or_404(Classroom, id=classroom_id)

    # Base queryset: chỉ câu hỏi của giáo viên hiện tại
    base_qs = Question.objects.filter(owner=request.user).order_by('-id')

    if request.method == 'POST':
        form = CreateExamForm(request.POST, initial=initial)
        # cần render danh sách câu hỏi đúng bộ lọc đã submit
        qs = base_qs
        if form.is_valid():
            kw = form.cleaned_data.get('q_keyword') or ''
            rate = form.cleaned_data.get('q_rate') or ''
            subject = form.cleaned_data.get('q_subject') or ''
            grade = form.cleaned_data.get('q_grade') or ''
            if kw:
                qs = qs.filter(content__icontains=kw)
            if rate:
                # dựa theo field của bạn: 'rate' hay 'level_rate'
                if hasattr(Question, 'rate'):
                    qs = qs.filter(rate=rate)
                elif hasattr(Question, 'level_rate'):
                    qs = qs.filter(level_rate=rate)
            if subject and hasattr(Question, 'subject'):
                qs = qs.filter(subject__icontains=subject)
            if grade and hasattr(Question, 'grade'):
                qs = qs.filter(grade__icontains=grade)
        else:
            qs = base_qs

        # Lấy các id câu hỏi được tick
        selected_ids = request.POST.getlist('selected_questions')
        if not selected_ids:
            messages.error(request, "Bạn chưa chọn câu hỏi nào.")
        elif form.is_valid():
            classroom = form.cleaned_data['classroom']
            title = form.cleaned_data['title']
            duration = form.cleaned_data['duration']
            start_time = form.cleaned_data.get('start_time')
            end_time = form.cleaned_data.get('end_time')

            exam = Exam()
            _assign_exam_fields(exam,
                                classroom=classroom,
                                title=title,
                                duration=duration,
                                start_time=start_time,
                                end_time=end_time,
                                user=request.user)
            exam.save()

            # Tạo ExamQuestion theo đúng thứ tự người dùng thấy/submit
            # (giữ nguyên thứ tự ID gửi lên)
            order = 1
            qs_map = {q.id: q for q in Question.objects.filter(id__in=selected_ids)}
            for sid in selected_ids:
                q = qs_map.get(int(sid))
                if q:
                    ExamQuestion.objects.create(exam=exam, question=q, order=order)
                    order += 1

            messages.success(request, f"Đã tạo đề “{getattr(exam,'title',getattr(exam,'name',''))}” với {order-1} câu hỏi.")
            try:
                return redirect('classroom_detail', class_id=classroom.id)
            except Exception:
                return redirect('question_list')
        # nếu lỗi -> render lại cùng thông báo
    else:
        form = CreateExamForm(initial={
            **initial,
            'title': f'Đề mới - {timezone.localtime().strftime("%d/%m/%Y %H:%M")}'
        })
        qs = base_qs

    # Áp dụng bộ lọc trên GET để xem danh sách
    if request.method == 'GET':
        kw = request.GET.get('q_keyword', '')
        rate = request.GET.get('q_rate', '')
        subject = request.GET.get('q_subject', '')
        grade = request.GET.get('q_grade', '')
        if kw:
            qs = qs.filter(content__icontains=kw)
            form.fields['q_keyword'].initial = kw
        if rate:
            if hasattr(Question, 'rate'):
                qs = qs.filter(rate=rate)
            elif hasattr(Question, 'level_rate'):
                qs = qs.filter(level_rate=rate)
            form.fields['q_rate'].initial = rate
        if subject and hasattr(Question, 'subject'):
            qs = qs.filter(subject__icontains=subject)
            form.fields['q_subject'].initial = subject
        if grade and hasattr(Question, 'grade'):
            qs = qs.filter(grade__icontains=grade)
            form.fields['q_grade'].initial = grade

    paginator = Paginator(qs, 10)  # 10 câu/ trang
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    return render(request, 'exam/create.html', {
        'form': form,
        'page_obj': page_obj,
    })


def _model_has_field(model, name: str) -> bool:
    return any(f.name == name for f in model._meta.get_fields())


def _get_exam_title(exam: Exam):
    return getattr(exam, 'title', getattr(exam, 'name', ''))


def _get_exam_duration(exam: Exam):
    return getattr(exam, 'duration_minutes', getattr(exam, 'duration', None))


def _get_exam_times(exam: Exam):
    st = None; et = None
    for fld in ['start_time', 'open_time', 'start_at', 'available_from']:
        if hasattr(exam, fld): st = getattr(exam, fld, None); break
    for fld in ['end_time', 'close_time', 'end_at', 'available_to', 'deadline']:
        if hasattr(exam, fld): et = getattr(exam, fld, None); break
    return st, et


def _is_owner(exam: Exam, user) -> bool:
    if getattr(user, 'is_superuser', False):
        return True
    for fld in ['created_by', 'creator', 'owner', 'teacher']:
        if hasattr(exam, fld) and getattr(exam, fld) == user:
            return True
    # fallback theo classroom
    if hasattr(exam, 'classroom'):
        cl = getattr(exam, 'classroom', None)
        if cl and (getattr(cl, 'owner', None) == user or getattr(cl, 'teacher', None) == user):
            return True
    return False


class ExamEditForm(forms.Form):
    classroom = forms.ModelChoiceField(queryset=Classroom.objects.all(), label="Lớp học")
    title = forms.CharField(max_length=255, label="Tiêu đề")
    duration = forms.IntegerField(min_value=1, label="Thời lượng (phút)")
    start_time = forms.DateTimeField(
        required=False, label="Thời gian mở",
        widget=forms.DateTimeInput(attrs={"type": "datetime-local"})
    )
    end_time = forms.DateTimeField(
        required=False, label="Thời gian đóng",
        widget=forms.DateTimeInput(attrs={"type": "datetime-local"})
    )

    def clean(self):
        data = super().clean()
        st, et = data.get("start_time"), data.get("end_time")
        if st and et and et <= st:
            self.add_error("end_time", "Thời gian đóng phải sau thời gian mở.")
        return data


@login_required
@role_required('teacher')
def exam_list(request, classroom_id=None):
    """Danh sách đề thi của giáo viên (lọc theo lớp, từ khoá, code)."""
    qs = Exam.objects.all().order_by('-id')

    # chỉ các exam do giáo viên hiện tại sở hữu
    q_owner = Q()
    for fld in ['created_by', 'creator', 'owner', 'teacher']:
        if _model_has_field(Exam, fld):
            q_owner |= Q(**{fld: request.user})
    if _model_has_field(Exam, 'classroom'):
        # thử lọc theo classroom.owner/teacher nếu có
        if _model_has_field(Classroom, 'owner'):
            q_owner |= Q(classroom__owner=request.user)
        if _model_has_field(Classroom, 'teacher'):
            q_owner |= Q(classroom__teacher=request.user)
    if q_owner:
        qs = qs.filter(q_owner).distinct()

    # filter classroom
    if classroom_id:
        if _model_has_field(Exam, 'classroom'):
            qs = qs.filter(classroom_id=classroom_id)

    # keyword (title/name/code)
    kw = request.GET.get('kw', '').strip()
    if kw:
        q_kw = Q()
        if _model_has_field(Exam, 'title'):
            q_kw |= Q(title__icontains=kw)
        if _model_has_field(Exam, 'name'):
            q_kw |= Q(name__icontains=kw)
        if _model_has_field(Exam, 'code'):
            q_kw |= Q(code__icontains=kw)
        if q_kw:
            qs = qs.filter(q_kw)

    # annotate số câu hỏi
    qs = qs.annotate(qcount=Count('questions', distinct=True)).select_related('classroom').prefetch_related('questions')
    # nếu related_name khác 'examquestion', fallback tính tay ở template

    # pagination
    from django.core.paginator import Paginator
    page_obj = Paginator(qs, 12).get_page(request.GET.get('page', 1))

    return render(request, 'exam/exam_list.html', {
        'page_obj': page_obj,
        'kw': kw,
        'classroom_id': classroom_id,
    })


@login_required
@role_required('teacher')
def exam_edit(request, exam_id):
    """Chỉnh sửa thông tin đề thi."""
    exam = get_object_or_404(Exam, id=exam_id)
    if not _is_owner(exam, request.user):
        messages.error(request, "Bạn không có quyền sửa đề này.")
        return redirect('exam_list')

    st, et = _get_exam_times(exam)
    init = {
        'classroom': getattr(exam, 'classroom', None),
        'title': _get_exam_title(exam),
        'duration': _get_exam_duration(exam) or 45,
        'start_time': st,
        'end_time': et,
    }

    if request.method == 'POST':
        form = ExamEditForm(request.POST, initial=init)
        if form.is_valid():
            _assign_exam_fields(
                exam,
                classroom=form.cleaned_data['classroom'],
                title=form.cleaned_data['title'],
                duration=form.cleaned_data['duration'],
                start_time=form.cleaned_data.get('start_time'),
                end_time=form.cleaned_data.get('end_time'),
                user=request.user
            )
            exam.save()
            messages.success(request, "Đã cập nhật đề thi.")
            return redirect('exam_list')
    else:
        form = ExamEditForm(initial=init)

    return render(request, 'exam/exam_edit.html', {
        'form': form,
        'exam': exam,
    })


@login_required
@role_required('teacher')
def exam_delete(request, exam_id):
    """Xoá đề thi (xác nhận)."""
    exam = get_object_or_404(Exam, id=exam_id)
    if not _is_owner(exam, request.user):
        messages.error(request, "Bạn không có quyền xoá đề này.")
        return redirect('exam_list')

    if request.method == 'POST':
        title = _get_exam_title(exam)
        exam.delete()  # ExamQuestion sẽ CASCADE nếu FK đã cấu hình đúng
        messages.success(request, f"Đã xoá đề “{title}”.")
        return redirect('exam_list')

    return render(request, 'exam/confirm_delete.html', {'exam': exam})


def _get_exam_start(exam):
    for fld in ['start_time', 'open_time', 'start_at', 'available_from']:
        if hasattr(exam, fld):
            return getattr(exam, fld)
    return None


def _get_exam_end(exam):
    for fld in ['end_time', 'close_time', 'end_at', 'available_to', 'deadline']:
        if hasattr(exam, fld):
            return getattr(exam, fld)
    return None


@login_required
@role_required('student')
def student_exams(request):
    """
    Danh sách kỳ thi mà học sinh có quyền tham gia:
    - Lấy theo các lớp mà học sinh đã tham gia (ClassroomStudent).
    - Tìm kiếm theo tiêu đề / tên / mã đề (?kw=).
    - Tính trạng thái cho từng Exam: upcoming/open/closed/in_process/submitted.
    """
    user = request.user
    now = timezone.now()

    # Lấy các lớp học sinh đang ở
    class_ids = list(
        Classroom.objects.filter(students__id_student=user)
        .values_list('id', flat=True).distinct()
    )

    # Base queryset: các Exam thuộc các lớp đó
    qs = Exam.objects.all()
    if hasattr(Exam, 'classroom'):
        qs = qs.filter(classroom_id__in=class_ids)

    # Tìm kiếm từ khoá
    kw = (request.GET.get('kw') or '').strip()
    if kw:
        q_kw = Q()
        if hasattr(Exam, 'title'):
            q_kw |= Q(title__icontains=kw)
        if hasattr(Exam, 'name'):
            q_kw |= Q(name__icontains=kw)
        if hasattr(Exam, 'code'):
            q_kw |= Q(code__icontains=kw)
        if q_kw:
            qs = qs.filter(q_kw)

    # Sắp xếp: ưu tiên theo thời gian mở nếu có, fallback theo id mới nhất
    if hasattr(Exam, 'start_time'):
        qs = qs.order_by('-start_time', '-id')
    elif hasattr(Exam, 'open_time'):
        qs = qs.order_by('-open_time', '-id')
    else:
        qs = qs.order_by('-id')

    # Phân trang
    page_obj = Paginator(qs, 10).get_page(request.GET.get('page', 1))

    # Tính trạng thái cho từng exam (và gắn vào instance để template dùng e.status)
    exam_ids = [e.id for e in page_obj.object_list]
    # Map StudentExam theo exam_id
    se_by_exam = {}
    for se in StudentExam.objects.filter(student=user, exam_id__in=exam_ids).order_by('-id'):
        se_by_exam.setdefault(se.exam_id, se)

    def compute_status(e):
        st = _get_exam_start(e)
        et = _get_exam_end(e)
        se = se_by_exam.get(e.id)

        # Trạng thái theo StudentExam nếu có
        if se:
            status = getattr(se, 'status', None)
            if status in ('submitted', 'in_process', 'joined'):
                return status

        # Nếu không có SE hoặc không có status rõ ràng -> tính theo thời gian
        if st and now < st:
            return 'upcoming'
        if et and now > et:
            return 'closed'
        # nếu không có start -> coi như 'open' đến khi quá et
        return 'open'

    # Gắn thuộc tính status để template dùng {{ e.status }}
    for e in page_obj.object_list:
        setattr(e, 'status', compute_status(e))

    return render(request, 'exam/student_exams.html', {
        'page_obj': page_obj,
        'kw': kw,
    })