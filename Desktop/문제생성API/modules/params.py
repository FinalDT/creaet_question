import azure.functions as func
from .database import get_question_data
from .responses import create_error_response, create_parameter_missing_response, create_invalid_format_response


def process_request_parameters(req: func.HttpRequest):
    """요청 파라미터 처리 및 검증"""

    # GET 요청에서 query parameter 받기
    grade = req.params.get('grade')
    term = req.params.get('term')
    topic_name = req.params.get('topic_name')
    question_type = req.params.get('question_type')
    difficulty_str = req.params.get('difficulty')
    count_str = req.params.get('count', '1')

    # 파라미터가 없으면 SQL에서 가져오기
    if not grade:
        sql_params = get_question_data("params")
        if not sql_params:
            return None, create_error_response(
                "Failed to get parameters from SQL",
                status_code=500
            )

        from .utils import get_grade_international
        print(f"🔍 ID:{sql_params['id']}에서 가져온 파라미터: {get_grade_international(sql_params['grade'])} {sql_params['term']}학기 - {sql_params['topic_name']} ({sql_params['question_type']}, 난이도{sql_params['difficulty']})")
        return {
            'grade': sql_params['grade'],
            'term': sql_params['term'],
            'topic_name': sql_params['topic_name'],
            'question_type': sql_params['question_type'],
            'difficulty': sql_params['difficulty'],
            'count': 1
        }, None

    else:
        # URL 파라미터가 있을 때 타입 변환 및 검증
        try:
            difficulty = int(difficulty_str) if difficulty_str else None
            count = int(count_str)
        except (ValueError, TypeError):
            return None, create_invalid_format_response()

        # 필수 파라미터 검증
        if not all([grade, term, topic_name, question_type, difficulty]):
            return None, create_parameter_missing_response()

        return {
            'grade': grade,
            'term': term,
            'topic_name': topic_name,
            'question_type': question_type,
            'difficulty': difficulty,
            'count': count
        }, None