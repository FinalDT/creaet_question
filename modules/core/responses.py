import json


def create_error_response(error_message, status_code=400, **extra_data):
    """에러 응답 생성 (딕셔너리 반환)"""
    response_data = {
        "error": error_message,
        "status_code": status_code
    }
    response_data.update(extra_data)
    return response_data


def create_success_response(data, status_code=200):
    """성공 응답 생성 (딕셔너리 반환)"""
    if isinstance(data, dict):
        data["status_code"] = status_code
        return data
    else:
        return {
            "data": data,
            "status_code": status_code
        }


def create_parameter_missing_response():
    """파라미터 누락 에러 응답"""
    return create_error_response(
        "Required parameters missing",
        required=["grade", "term", "topic_name", "question_type", "difficulty"],
        example_url="http://localhost:7071/api/create_question?grade=M2&term=1&topic_name=일차함수의 함숫값 구하기&question_type=단답형&difficulty=3"
    )


def create_invalid_format_response():
    """잘못된 형식 에러 응답"""
    return create_error_response(
        "Invalid parameter format",
        message="difficulty and count must be integers"
    )


def create_question_success_response(generated_questions):
    """문제 생성 성공 응답"""
    return create_success_response({
        "success": True,
        "generated_questions": generated_questions,
        "count": len(generated_questions),
        "validation": {
            "format_check": "passed",
            "db_storage": "disabled_for_testing"
        }
    })


def create_question_failed_response():
    """문제 생성 실패 응답"""
    return create_error_response(
        "Failed to generate valid questions",
        status_code=500,
        success=False,
        generated_questions=[],
        count=0
    )