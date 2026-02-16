from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from .models import StudentAnswer, StudentExam


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def autosave_answers(request):
    student_exam_id = request.data.get('student_exam_id')
    answers = request.data.get('answers')  # dict {question_id: answer}

    try:
        student_answer = StudentAnswer.objects.get(student_exam_id=student_exam_id, student_exam__student=request.user)
    except StudentAnswer.DoesNotExist:
        return Response({'error': 'Không tìm thấy bài làm.'}, status=status.HTTP_404_NOT_FOUND)

    if not isinstance(answers, dict):
        return Response({'error': 'Sai kiểu dữ liệu answers.'}, status=status.HTTP_400_BAD_REQUEST)

    student_answer.backup_answers = answers
    student_answer.save(update_fields=['backup_answers', 'last_backup'])

    return Response({'message': 'Đã lưu tạm đáp án.'}, status=status.HTTP_200_OK)
