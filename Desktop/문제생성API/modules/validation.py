import logging
from .database import get_question_data


def validate_question_format(question_data, expected_type):
    """문제 형식 검증"""
    required_fields = ['question_text', 'question_type', 'correct_answer', 'answer_explanation']

    # 필수 필드 확인
    for field in required_fields:
        if field not in question_data:
            logging.error(f"Missing required field: {field}")
            return False

    # 선택형인 경우 choices 필드 확인
    if expected_type == '선택형':
        if 'choices' not in question_data or not isinstance(question_data['choices'], list):
            logging.error("선택형 문제에 choices가 없습니다")
            return False
        if len(question_data['choices']) != 5:
            logging.error("선택형 문제는 5개의 선택지가 필요합니다")
            return False

    # 기본 길이 검증
    if len(question_data['question_text']) < 10:
        logging.error("문제 내용이 너무 짧습니다")
        return False

    if len(question_data['answer_explanation']) < 10:
        logging.error("해설이 너무 짧습니다")
        return False

    return True


def prepare_question_record(question_id, grade, term, topic_name, question_type, difficulty, question_data):
    """questions_dim 테이블용 레코드 준비"""
    return {
        'id': question_id,
        'question_grade': grade,
        'question_term': term,
        'question_unit': '00',  # 기본값
        'question_topic': get_question_data("topic_code", topic_name),
        'question_topic_name': topic_name,
        'question_type1': question_type,
        'question_type2': '0',
        'question_sector1': '계산',
        'question_sector2': '변화와 관계',
        'question_step': '기본',
        'question_difficulty': difficulty,
        'question_text': question_data['question_text'],
        'question_filename': '',  # 이미지 없음
        'similar_question': '',
        'question_condition': '1'
    }


def prepare_answer_record(question_id, question_data):
    """answers_dim 테이블용 레코드 준비"""
    return {
        'id': question_id,
        'answer_filename': '',  # 이미지 없음
        'answer_text': question_data['answer_explanation'],
        'answer_by_ai': question_data['correct_answer']
    }