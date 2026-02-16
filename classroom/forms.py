from django import forms
from .models import Classroom


class ClassroomForm(forms.ModelForm):
    class Meta:
        model = Classroom
        fields = ['name', 'description', 'status']


class JoinClassroomForm(forms.Form):
    code = forms.CharField(max_length=8, label="Nhập mã lớp học")