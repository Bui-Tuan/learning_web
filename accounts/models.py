from django.db import models
from django.contrib.auth.models import AbstractUser

# Create your models here.


class User(AbstractUser):
    role_choices = (
        ('admin', 'Admin'),
        ('teacher', 'Teacher'),
        ('student', 'Student')
    )
    role = models.CharField(max_length=10, choices=role_choices)
    avatar = models.ImageField(upload_to='avatar/', null=True, blank=True)
    full_name = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.full_name} ({self.role})"
