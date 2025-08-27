from django.db import models
import random, string
from django.conf import settings

# Create your models here.


def generate_unique_code():
    
    while True:
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        if not Classroom.objects.filter(code=code).exists():
            return code


class Classroom(models.Model):
    status_choices = (
        ('open', 'Open'),
        ('close', 'Close'),
        ('wait', 'Coming soon')

    )
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=status_choices)
    code = models.CharField(max_length=8, unique=True, editable=False)
    id_teacher = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    create_time = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = generate_unique_code()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.code})"


class ClassroomStudent(models.Model):
    id_classroom = models.ForeignKey('Classroom', on_delete=models.CASCADE, related_name='students')
    id_student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='classrooms_joined')
    join_time = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('id_classroom', 'id_student')  # Mỗi học sinh chỉ vào 1 lớp 1 lần

    def __str__(self):
        return f"{self.id_student.full_name} in {self.id_classroom.name}"


