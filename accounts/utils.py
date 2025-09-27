# student/views.py (hoặc accounts/views_student.py)
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Avg
from django.shortcuts import render
from django.utils import timezone

from question.decorators import role_required
from classroom.models import Classroom
from exam.models import Exam
from answer.models import StudentExam


# ===== Helpers linh hoạt tên field =====
def _model_has_field(model, name: str) -> bool:
    return any(f.name == name for f in model._meta.get_fields())


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


def _get_studentexam_score(se):
    for fld in ['score', 'mark', 'points', 'total_score']:
        if hasattr(se, fld):
            return getattr(se, fld)
    return None


def _get_studentexam_submitted_at(se):
    for fld in ['submitted_at', 'submit_time', 'submitted_time', 'submitted_on']:
        if hasattr(se, fld):
            return getattr(se, fld)
    # fallback: nếu có status
    if hasattr(se, 'status') and getattr(se, 'status') == 'submitted':
        # không có thời gian cụ thể
        return timezone.now()
    return None