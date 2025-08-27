from django.db import models
from django.utils import timezone
import random, string

from classroom.models import Classroom
from question.models import Question  # hoặc từ app tương ứng bạn tạo câu hỏi
from django.conf import settings


def generate_exam_code():
    while True:
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        if not Exam.objects.filter(code=code).exists():
            return code


class Exam(models.Model):
    classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE, related_name='exams')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    open_time = models.DateTimeField()
    close_time = models.DateTimeField()
    duration_minutes = models.PositiveIntegerField()
    max_attempts = models.PositiveIntegerField(default=1)
    create_time = models.DateTimeField(auto_now_add=True)
    total_questions = models.PositiveIntegerField(default=0)
    code = models.CharField(max_length=8, unique=True, editable=False)

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = generate_exam_code()

        super().save(*args, **kwargs)

    def is_open(self):
        now = timezone.now()
        return self.open_time <= now <= self.close_time

    def __str__(self):
        return f"{self.name} - {self.classroom.name}"


class ExamQuestion(models.Model):
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='questions')
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    position = models.PositiveIntegerField()  # Vị trí câu hỏi trong bài thi

    class Meta:
        unique_together = ('exam', 'question')
        ordering = ['position']

    def __str__(self):
        return f"Q{self.position} in {self.exam.name}"
