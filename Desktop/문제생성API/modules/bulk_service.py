import logging
from .database import get_question_data, get_sql_connection
from .ai_service import get_openai_client, generate_question_with_ai
from .validation import validate_question_format, prepare_question_record, prepare_answer_record
from .utils import generate_question_id
from .responses import create_success_response, create_error_response
from .debug import print_question_result


def get_multiple_question_params(limit=4):
    """여러 개의 문제 파라미터 가져오기"""
    try:
        conn = get_sql_connection()
        if not conn:
            return None

        cursor = conn.cursor()
        cursor.execute(f"""
            SELECT TOP {limit} id, question_grade, question_term, question_topic_name, question_type1, question_difficulty
            FROM questions_dim
            ORDER BY id
        """)
        results = cursor.fetchall()
        conn.close()

        if results:
            return [
                {
                    'id': result[0],
                    'grade': result[1],
                    'term': result[2],
                    'topic_name': result[3],
                    'question_type': result[4],
                    'difficulty': result[5]
                }
                for result in results
            ]
        return None

    except Exception as e:
        logging.error(f"Error getting multiple question params: {str(e)}")
        return None


def handle_bulk_generation(req):
    """대량 문제 생성 처리 (20개 = 4개 ID × 5개씩)"""
    logging.info('Bulk question generation API called')

    try:
        # 4개의 서로 다른 파라미터 세트 가져오기
        param_sets = get_multiple_question_params(4)
        if not param_sets:
            return create_error_response(
                "Failed to get question parameters from SQL",
                status_code=500
            )

        print("🚀 대량 문제 생성 시작 (총 20개)")
        print("=" * 80)

        client = get_openai_client()
        all_generated_questions = []

        for set_idx, params in enumerate(param_sets, 1):
            from .utils import get_grade_international
            print(f"\n📋 세트 {set_idx}/4 - ID:{params['id']}에서 가져온 파라미터")
            print(f"   {get_grade_international(params['grade'])} {params['term']}학기 - {params['topic_name']} ({params['question_type']}, 난이도{params['difficulty']})")

            # 해당 주제의 기존 문제들 가져오기
            existing_questions = get_question_data("questions", params['topic_name'])

            set_questions = []
            generated_problems = []  # 이미 생성된 문제들 추적

            # 각 세트당 5개 문제 생성
            for i in range(5):
                question_data = generate_question_with_ai(
                    client, params['grade'], params['term'], params['topic_name'],
                    params['question_type'], params['difficulty'], existing_questions, generated_problems
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
                    question_result = {
                        "id": question_id,
                        "source_id": params['id'],  # 원본 ID 추가
                        **question_data,
                        "metadata": {
                            "grade": params['grade'],
                            "term": params['term'],
                            "topic_name": params['topic_name'],
                            "difficulty": params['difficulty'],
                            "set_number": set_idx
                        }
                    }

                    set_questions.append(question_result)
                    all_generated_questions.append(question_result)

                    # 생성된 문제를 추적 리스트에 추가
                    generated_problems.append(question_data['question_text'][:100])

                    # 간단한 디버그 출력
                    total_count = (set_idx - 1) * 5 + len(set_questions)
                    print(f"   ✅ {total_count:2d}/20 - {question_data['question_text'][:50]}...")
                else:
                    logging.warning(f"Question validation failed for set {set_idx}, question {i+1}")

            print(f"   📊 세트 {set_idx} 완료: {len(set_questions)}/5개 문제 생성")

        print("\n" + "=" * 80)
        print(f"🎯 대량 생성 완료: 총 {len(all_generated_questions)}/20개 문제")
        print("=" * 80)

        # 요약 정보 생성
        summary = {
            "total_generated": len(all_generated_questions),
            "target_count": 20,
            "sets_processed": len(param_sets),
            "questions_per_set": [
                len([q for q in all_generated_questions if q['metadata']['set_number'] == i])
                for i in range(1, len(param_sets) + 1)
            ]
        }

        return create_success_response({
            "success": True,
            "generated_questions": all_generated_questions,
            "summary": summary,
            "validation": {
                "format_check": "passed",
                "db_storage": "disabled_for_testing"
            }
        })

    except Exception as e:
        logging.error(f"Error in bulk generation: {str(e)}")
        return create_error_response(f"Failed to generate bulk questions: {str(e)}", status_code=500)