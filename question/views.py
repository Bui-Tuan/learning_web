# question/views.py
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from .forms import QuestionForm, ChoiceFormSet, UploadFileForm
from .models import Question, QuestionImage, QuestionChoice
from .decorators import role_required
import pprint
import tempfile
import pypandoc
import os
from .utils import parse_docx
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt


@login_required
@role_required('teacher')
def create_question(request):
    if request.method == 'POST':
        form = QuestionForm(request.POST, request.FILES)
        formset = ChoiceFormSet(request.POST, request.FILES)
        if form.is_valid() and formset.is_valid():
            question = form.save(commit=False)
            question.owner = request.user
            question.save()
            choices = formset.save(commit=False)
            for choice in choices:
                choice.question = question
                choice.save()
            # Lưu các ảnh đề bài (multi)
            images = request.FILES.getlist('images')
            for img in images:
                QuestionImage.objects.create(question=question, image=img)
            return redirect('question_list')
    else:
        form = QuestionForm()
        formset = ChoiceFormSet()
    return render(request, 'question/create_question.html', {
        'form': form,
        'formset': formset,
    })


@login_required
@role_required('teacher')
def question_list(request):
    questions = Question.objects.prefetch_related('images', 'choices').order_by('-create_time')
    return render(request, 'question/question_list.html', {'questions': questions})


@login_required
@role_required('teacher')
def edit_question(request, question_id):
    question = get_object_or_404(Question, id=question_id)
    # Lấy danh sách ảnh cũ
    images = question.images.all()

    if request.method == 'POST':
        q_form = QuestionForm(request.POST, instance=question)
        formset = ChoiceFormSet(request.POST, instance=question)
        new_images = request.FILES.getlist('images')  # images là trường FileField(multiple) ở form

        # Xử lý xóa ảnh cũ
        images_to_delete = request.POST.getlist('delete_images')  # checkbox name="delete_images"
        for img_id in images_to_delete:
            img_obj = QuestionImage.objects.filter(id=img_id, question=question).first()
            if img_obj:
                img_obj.delete()

        if q_form.is_valid() and formset.is_valid():
            q_form.save()
            formset.save()
            # Thêm ảnh mới
            for img in new_images:
                QuestionImage.objects.create(question=question, image=img)
            return redirect('question_list')

    else:
        q_form = QuestionForm(instance=question)
        formset = ChoiceFormSet(instance=question)

    return render(request, 'question/edit_question.html', {
        'q_form': q_form,
        'formset': formset,
        'images': images,   # truyền ra template để show và chọn xóa
    })


@login_required
@role_required('teacher')
def delete_question(request, question_id):
    question = get_object_or_404(Question, id=question_id)

    if request.method == 'POST':
        question.delete()
        return redirect('question_list')

    return render(request, 'question/question_delete.html', {'question': question})


@login_required
@role_required('teacher')
def upload_file(request):
    if request.method == 'POST':
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            file = request.FILES['file']

            # 1. Lưu file docx tạm
            with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as temp_docx:
                for chunk in file.chunks():
                    temp_docx.write(chunk)
                temp_path = temp_docx.name

            # 2. Đường dẫn lưu ảnh media trích xuất từ docx
            tmp_media_dir = tempfile.mkdtemp(prefix="pandoc_media_")

            try:
                # 3. Chuyển file sang LaTeX và trích ảnh
                latex_text = pypandoc.convert_file(
                    temp_path, 'latex', extra_args=[f'--extract-media={tmp_media_dir}']
                )
            finally:
                os.remove(temp_path)

            # 4. Duyệt folder ảnh, có thể dùng cho mapping ảnh vào question
            image_files = []
            for root, dirs, files in os.walk(tmp_media_dir):
                for f in files:
                    image_files.append(os.path.join(root, f))
            print(latex_text)
            # 5. Parse LaTeX sang danh sách câu hỏi Python dict
            questions = parse_docx(latex_text, tmp_media_dir)  # Trả về list dict (xem dưới)

            print(questions)
            if not questions:
                return render(request, 'question/edit_uploaded_questions.html', {
                    'questions': [],
                    'MEDIA_URL': settings.MEDIA_URL,
                    'tmp_media_dir': tmp_media_dir,
                    'debug_latex': latex_text[:3000],  # xem nhanh trong template
                    'parse_warning': 'Không parse được câu hỏi. Kiểm tra lại format dòng Mức độ/Đáp án hoặc regex trong parse_docx.'
                })
            # 6. Lưu vào session để preview và chọn chỉnh sửa trước khi lưu DB
            request.session['parsed_questions'] = questions
            # Nếu cần debug:
            for idx, q in enumerate(questions):
                print(f"Câu hỏi {idx + 1}:", q)

            return render(
                request, 'question/edit_uploaded_questions.html',
                {'questions': questions, 'MEDIA_URL': settings.MEDIA_URL, 'tmp_media_dir': tmp_media_dir}
            )
    else:
        form = UploadFileForm()

    return render(request, 'question/upload.html', {'form': form})


@login_required
@role_required('teacher')
@csrf_exempt
def save_questions(request):
    """
    Lưu hàng loạt câu hỏi từ session hoặc từ form preview vào database.
    """
    data = request.POST
    files = request.FILES
    i = 1
    created_question_ids = []

    # Duyệt tất cả các câu hỏi đã preview
    while f"latex_question_{i}" in data:
        # --- Lấy nội dung câu hỏi
        question_content = data.get(f"latex_question_{i}", "").strip()
        rate = data.get(f"rate_{i}", "Dễ")   # Hoặc mặc định "NB"
        answer_letter = data.get(f"answer_{i}", "A")

        # Tạo mới Question (sửa field cho đúng model của bạn!)
        question = Question.objects.create(
            content=question_content,
            rate=rate,
            correct_answer=answer_letter,
            owner=request.user if request.user.is_authenticated else None,
        )
        created_question_ids.append(str(question.id))

        # --- Lưu danh sách đáp án A-D
        for j in range(4):
            choice_text = data.get(f"latex_option_{i}_{j}", "").strip()
            label = chr(65 + j)  # A/B/C/D
            QuestionChoice.objects.create(
                question=question,
                label=label,
                text=choice_text,
            )

        # --- Lưu ảnh (nếu có nhiều ảnh từ preview)
        k = 0
        while True:
            img_name = data.get(f"existing_question_image_{i}_{k}", None)
            if not img_name:
                break
            QuestionImage.objects.create(
                question=question,
                image=img_name,  # Đường dẫn tương đối đã lưu sẵn khi parse_docx
            )
            k += 1

        # --- Nếu có upload file ảnh mới (không qua docx): (tùy chọn, thường không dùng)
        # image_file = files.get(f"question_image_{i}", None)
        # if image_file:
        #     QuestionImage.objects.create(question=question, image=image_file)

        i += 1

    # Ghi lại danh sách id vừa import để dùng cho bước tạo exam từ question
    request.session['last_uploaded_question_ids'] = created_question_ids

    return render(request, 'question/success.html')