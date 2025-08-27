# question/forms.py
from django import forms
from .models import Question, QuestionImage, QuestionChoice, ANSWER_CHOICES


class MultiFileClearableInput(forms.ClearableFileInput):
    allow_multiple_selected = True          # 🔑 bật hỗ trợ nhiều file


class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = ['content', 'rate', 'correct_answer']

    images = forms.FileField(
        widget=MultiFileClearableInput(attrs={'multiple': True}),
        required=False,
        label="Ảnh minh họa đề bài"
    )


class QuestionChoiceForm(forms.ModelForm):
    class Meta:
        model = QuestionChoice
        fields = ['label', 'text', 'image']


ChoiceFormSet = forms.inlineformset_factory(
    Question, QuestionChoice,
    form=QuestionChoiceForm,
    extra=4,
    min_num=4,
    validate_min=True,
    max_num=4,
    validate_max=True,
    can_delete=False
)


class UploadFileForm(forms.Form):
    file = forms.FileField()