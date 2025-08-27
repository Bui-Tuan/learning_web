from django.db import models
from django.conf import settings

ANSWER_CHOICES = (
    ('A', 'A'),
    ('B', 'B'),
    ('C', 'C'),
    ('D', 'D'),
)

level_rate = [
        ('Dễ', 'Dễ'),
        ('Trung Bình', 'Trung Bình'),
        ('Khó', 'Khó'),
    ]


class Question(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='questions')
    content = models.TextField(blank=True)  # Nội dung đề bài, có thể chứa LaTeX
    rate = models.CharField(max_length=20, choices=level_rate, default='Dễ', verbose_name='Độ khó')
    create_time = models.DateTimeField(auto_now_add=True)
    correct_answer = models.CharField(max_length=1, choices=ANSWER_CHOICES)

    def __str__(self):
        return f"Câu hỏi của {self.owner.full_name} - {self.id}"


class QuestionImage(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='question_images/')

    def __str__(self):
        return f"Ảnh đề bài - {self.question.id}"


class QuestionChoice(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='choices')
    label = models.CharField(max_length=1, choices=ANSWER_CHOICES)  # A/B/C/D
    text = models.TextField(blank=True, null=True)  # Nội dung phương án
    image = models.ImageField(upload_to='choice_images/', blank=True, null=True)  # Ảnh cho phương án (nếu có)

    def __str__(self):
        return f"{self.label} - {self.question.id}"
