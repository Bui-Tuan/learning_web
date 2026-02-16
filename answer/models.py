from django.db import models

# Create your models here.


from django.db import models
from django.conf import settings
from django.utils import timezone
from exam.models import Exam
from question.models import Question


class StudentExam(models.Model):
    STATUS_CHOICES = (
        ('joined', 'Đã tham gia'),
        ('in_process', 'Đang làm'),
        ('submitted', 'Đã nộp'),
    )

    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='exam_attempts')
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='student_exams')
    join_at = models.DateTimeField(auto_now_add=True)
    start_at = models.DateTimeField(null=True, blank=True)
    submit_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='joined')
    attempt_number = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ('student', 'exam', 'attempt_number')

    def __str__(self):
        return f"{self.student.full_name} - {self.exam.name} (Lần {self.attempt_number})"

    def start_exam(self):
        self.status = 'in_process'
        self.start_at = timezone.now()
        self.save(update_fields=['status', 'start_at'])

    def submit_exam(self):
        self.status = 'submitted'
        self.submit_at = timezone.now()
        self.save(update_fields=['status', 'submit_at'])


class StudentAnswer(models.Model):
    student_exam = models.OneToOneField(StudentExam, on_delete=models.CASCADE, related_name='answers')
    answers = models.JSONField(default=dict)  # Lưu dictionary {question_id: 'A' / 'B' / 'C' / 'D'}
    backup_answers = models.JSONField(default=dict) # Đáp án tạm (auto-save)
    last_backup = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Answer - {self.student_exam}"


class Score(models.Model):
    student_answer = models.OneToOneField(StudentAnswer, on_delete=models.CASCADE, related_name='score')
    total_score = models.DecimalField(max_digits=5, decimal_places=2)  # VD: 9.50 / 10.00
    calculated_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Score {self.total_score} for {self.student_answer.student_exam}"
