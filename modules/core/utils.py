import uuid
from datetime import datetime


def get_grade_description(grade):
    """학년 코드를 설명으로 변환 (AI 프롬프트용 - 한국 기준)"""
    # 정수형 grade 처리 추가
    if isinstance(grade, int):
        grade_map = {
            1: '중학교 1학년',
            2: '중학교 2학년',
            3: '중학교 3학년',
            7: '중학교 1학년',  # 국제 기준
            8: '중학교 2학년',
            9: '중학교 3학년'
        }
        return grade_map.get(grade, '중학교 2학년')

    # 문자열 grade 처리
    grade_map = {
        'M1': '중학교 1학년',
        'M2': '중학교 2학년',
        'M3': '중학교 3학년'
    }
    return grade_map.get(grade, '중학교 2학년')


def get_grade_international(grade):
    """학년 코드를 국제 기준으로 변환 (표시/저장용)"""
    # 정수형 grade 처리 추가
    if isinstance(grade, int):
        grade_map = {
            1: '중1',
            2: '중2',
            3: '중3',
            7: '중1',  # 국제 기준
            8: '중2',
            9: '중3'
        }
        return grade_map.get(grade, '중2')

    # 문자열 grade 처리
    grade_map = {
        'M1': '중1',
        'M2': '중2',
        'M3': '중3'
    }
    return grade_map.get(grade, '중2')


def generate_question_id():
    """고유한 문제 ID 생성"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_suffix = str(uuid.uuid4())[:8]
    return f"Q_{timestamp}_{unique_suffix}"