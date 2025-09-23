# -*- coding: utf-8 -*-
"""
learnerID 기반 개인화 문제 생성 서비스
기존 view_service 모듈들을 재사용
"""
import logging
import json
import azure.functions as func
from ..core.database import get_sql_connection, get_question_data, get_mapped_concept_name, get_knowledge_tag_by_concept
from ..core.ai_service import get_openai_client, generate_question_with_ai
from ..core.validation import validate_question_format, prepare_question_record, prepare_answer_record
from ..core.utils import generate_question_id, get_grade_international
from ..core.responses import create_success_response, create_error_response


def get_learner_requirements(learner_id):
    """특정 learnerID의 모든 요구사항 가져오기"""
    try:
        conn = get_sql_connection()
        if not conn:
            return None

        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                learnerID,
                assessmentItemID,
                knowledgeTag,
                grade,
                term,
                concept_name,
                chapter_name,
                difficulty_band,
                topic_name,
                unit_name
            FROM vw_personal_item_enriched
            WHERE learnerID = ?
            ORDER BY assessmentItemID
        """, (learner_id,))

        results = cursor.fetchall()
        conn.close()

        if results:
            return [
                {
                    'learner_id': result[0],
                    'assessment_item_id': result[1],
                    'knowledge_tag': result[2],
                    'grade': result[3],
                    'term': result[4],
                    'concept_name': result[5],
                    'chapter_name': result[6],
                    'difficulty_band': result[7],
                    'topic_name': result[8],
                    'unit_name': result[9]
                }
                for result in results
            ]
        return []

    except Exception as e:
        logging.error(f"Error getting learner requirements: {str(e)}")
        return None


def handle_personalized_generation(req):
    """learnerID 기반 개인화 문제 생성 처리"""
    logging.info('Personalized question generation API called')

    try:
        # learnerID 파라미터 받기
        learner_id = req.params.get('learnerID')
        if not learner_id:
            response_data = create_error_response(
                "learnerID parameter is required",
                status_code=400
            )
            return func.HttpResponse(
                json.dumps(response_data, ensure_ascii=False),
                status_code=400,
                headers={"Content-Type": "application/json; charset=utf-8"}
            )

        # 해당 learnerID의 요구사항 가져오기
        requirements = get_learner_requirements(learner_id)
        if requirements is None:
            response_data = create_error_response(
                "Failed to get learner requirements from database",
                status_code=500
            )
            return func.HttpResponse(
                json.dumps(response_data, ensure_ascii=False),
                status_code=500,
                headers={"Content-Type": "application/json; charset=utf-8"}
            )

        if not requirements:
            response_data = create_error_response(
                f"No data found for learnerID: {learner_id}",
                status_code=404
            )
            return func.HttpResponse(
                json.dumps(response_data, ensure_ascii=False),
                status_code=404,
                headers={"Content-Type": "application/json; charset=utf-8"}
            )

        print(f"[개인화 생성] learnerID: {learner_id}에 대한 문제 생성 시작 (총 {len(requirements)}개)")
        print("=" * 80)

        client = get_openai_client()
        all_generated_questions = []

        # concept_name별로 생성된 문제들 추적 (중복 방지용)
        concept_generated_problems = {}

        for req_idx, requirement in enumerate(requirements, 1):
            print(f"\n[요구사항 {req_idx}/{len(requirements)}] learnerID: {requirement['learner_id']}, assessmentItemID: {requirement['assessment_item_id']}")
            print(f"   {get_grade_international(requirement['grade'])} {requirement['term']}학기 - {requirement['concept_name']} (난이도: {requirement['difficulty_band']})")

            # 해당 주제의 기존 문제들 가져오기 (참고용)
            existing_questions = get_question_data("questions", requirement['topic_name'])

            # 해당 concept_name에서 이미 생성된 문제들 가져오기
            concept_key = requirement['concept_name']
            if concept_key not in concept_generated_problems:
                concept_generated_problems[concept_key] = []

            # 문제 생성 (기존 view_service와 동일한 로직)
            question_data = generate_question_with_ai(
                client,
                requirement['grade'],
                requirement['term'],
                requirement['concept_name'],  # topic_name 대신 concept_name 사용
                '선택형',  # 기본값, 필요시 파라미터화 가능
                requirement['difficulty_band'],
                existing_questions,
                concept_generated_problems[concept_key]
            )

            if question_data and validate_question_format(question_data, '선택형'):
                question_id = generate_question_id()

                # DB에서 미리 매핑된 concept_name 조회
                recommended_concept = get_mapped_concept_name(requirement['concept_name'])
                knowledge_tag = get_knowledge_tag_by_concept(recommended_concept) if recommended_concept else None

                # DB 저장 준비 (현재 비활성화)
                question_record = prepare_question_record(
                    question_id, requirement['grade'], requirement['term'], requirement['concept_name'],
                    '선택형', requirement['difficulty_band'], question_data
                )
                answer_record = prepare_answer_record(question_id, question_data)

                # 결과 추가
                question_result = {
                    "id": question_id,
                    "learner_id": requirement['learner_id'],
                    "assessment_item_id": requirement['assessment_item_id'],
                    **question_data,
                    "metadata": {
                        "grade": requirement['grade'],
                        "term": requirement['term'],
                        "concept_name": requirement['concept_name'],
                        "chapter_name": requirement['chapter_name'],
                        "topic_name": requirement['topic_name'],
                        "unit_name": requirement['unit_name'],
                        "difficulty_band": requirement['difficulty_band'],
                        "knowledge_tag": requirement['knowledge_tag'],
                        "mapped_concept_name": recommended_concept,
                        "mapped_knowledge_tag": knowledge_tag
                    }
                }

                all_generated_questions.append(question_result)

                # 생성된 문제를 추적 리스트에 추가
                concept_generated_problems[concept_key].append(question_data['question_text'][:100])

                print(f"   [성공] {req_idx}/{len(requirements)} - {question_data['question_text'][:50]}...")
                print(f"          concept_name: {requirement['concept_name']}")
                print(f"          knowledgeTag: {requirement['knowledge_tag']}")
                print()
            else:
                logging.warning(f"Question validation failed for learnerID {learner_id}, requirement {req_idx}")

        print("\n" + "=" * 80)
        print(f"[개인화 생성 완료] learnerID: {learner_id}, 총 {len(all_generated_questions)}/{len(requirements)}개 문제")
        print("=" * 80)

        # 요약 정보 생성
        summary = {
            "learner_id": learner_id,
            "total_generated": len(all_generated_questions),
            "total_requirements": len(requirements),
            "success_rate": round(len(all_generated_questions) / len(requirements) * 100, 1) if requirements else 0,
            "concepts_covered": len(set(req['concept_name'] for req in requirements))
        }

        response_data = create_success_response({
            "success": True,
            "generated_questions": all_generated_questions,
            "summary": summary,
            "validation": {
                "format_check": "passed",
                "db_storage": "disabled_for_testing"
            }
        })
        return func.HttpResponse(
            json.dumps(response_data, ensure_ascii=False),
            status_code=200,
            headers={"Content-Type": "application/json; charset=utf-8"}
        )

    except Exception as e:
        logging.error(f"Error in personalized generation: {str(e)}")
        response_data = create_error_response(f"Failed to generate personalized questions: {str(e)}", status_code=500)
        return func.HttpResponse(
            json.dumps(response_data, ensure_ascii=False),
            status_code=500,
            headers={"Content-Type": "application/json; charset=utf-8"}
        )