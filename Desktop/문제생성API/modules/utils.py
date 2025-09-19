import uuid
from datetime import datetime


def get_grade_description(grade):
    """학년 코드를 설명으로 변환 (AI 프롬프트용 - 한국 기준)"""
    grade_map = {
        'M1': '중학교 1학년',
        'M2': '중학교 2학년',
        'M3': '중학교 3학년'
    }
    return grade_map.get(grade, '중학교 2학년')


def get_grade_international(grade):
    """학년 코드를 국제 기준으로 변환 (표시/저장용)"""
    grade_map = {
        'M1': '7학년',
        'M2': '8학년',
        'M3': '9학년'
    }
    return grade_map.get(grade, '8학년')


def generate_question_id():
    """고유한 문제 ID 생성"""
    timestamp = datetime.now().strftime("%y%m%d")
    unique_suffix = str(uuid.uuid4())[:8]
    return f"AI{timestamp}_{unique_suffix}"