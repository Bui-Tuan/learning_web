from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User


class UserRegisterForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email'
        })
    )
    full_name = forms.CharField(max_length=255)
    role = forms.ChoiceField(choices=User.role_choices)
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your username'
        })
    )
    password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter password'
        })
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm password'
        })
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'full_name', 'role', 'password1', 'password2']


class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['full_name', 'email', 'avatar']
        widgets = {
            'full_name': forms.TextInput(attrs={'placeholder': 'Họ và tên'}),
            'email': forms.EmailInput(attrs={'placeholder': 'Email'}),
        }