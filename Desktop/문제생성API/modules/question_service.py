import logging
from .database import get_question_data
from .ai_service import get_openai_client, generate_question_with_ai
from .validation import validate_question_format, prepare_question_record, prepare_answer_record
from .utils import generate_question_id
from .params import process_request_parameters
from .responses import create_question_success_response, create_question_failed_response, create_error_response
from .debug import print_question_result


def handle_create_question(req):
    """문제 생성 요청 처리"""
    logging.info('Question creation API called')

    try:
        # 파라미터 처리
        params, error_response = process_request_parameters(req)
        if error_response:
            return error_response

        # 기존 문제들 가져오기
        existing_questions = get_question_data("questions", params['topic_name'])
        client = get_openai_client()
        generated_questions = []

        # 문제 생성 루프
        for i in range(params['count']):
            question_data = generate_question_with_ai(
                client, params['grade'], params['term'], params['topic_name'],
                params['question_type'], params['difficulty'], existing_questions
            )

            if question_data and validate_question_format(question_data, params['question_type']):
                question_id = generate_question_id()

                # DB 저장 준비 (현재 비활성화)
                question_record = prepare_question_record(
                    question_id, params['grade'], params['term'], params['topic_name'],
                    params['question_type'], params['difficulty'], question_data
                )
                answer_record = prepare_answer_record(question_id, question_data)

                # 결과 추가
                generated_questions.append({
                    "id": question_id,
                    **question_data,
                    "metadata": {
                        "grade": params['grade'],
                        "term": params['term'],
                        "topic_name": params['topic_name'],
                        "difficulty": params['difficulty']
                    }
                })

                # 디버그 출력
                print_question_result(question_data, i+1, params['grade'], params['term'], params['topic_name'])
            else:
                logging.warning(f"Question validation failed for attempt {i+1}")

        # 응답 반환
        if generated_questions:
            return create_question_success_response(generated_questions)
        else:
            return create_question_failed_response()

    except Exception as e:
        logging.error(f"Error in create_question: {str(e)}")
        return create_error_response(f"Failed to create question: {str(e)}", status_code=500)