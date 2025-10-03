# -*- coding: utf-8 -*-
"""
뷰 기반 개인화 문제 생성 서비스 (bulk_generate 구조 참고)
"""
import logging
import json
import azure.functions as func
from ..core.database import get_sql_connection, get_question_data, get_mapped_concept_name, get_knowledge_tag_by_concept
from ..core.ai_service import get_openai_client, generate_question_with_ai
from ..core.validation import validate_question_format, prepare_question_record, prepare_answer_record
from ..core.utils import generate_question_id
from ..core.responses import create_success_response, create_error_response


def get_sample_learner_requirements(limit=5):
    """vw_personal_item_enriched에서 샘플 학습자 요구사항 가져오기 (bulk_generate 스타일)"""
    try:
        conn = get_sql_connection()
        if not conn:
            return None

        cursor = conn.cursor()
        cursor.execute(f"""
            SELECT TOP {limit}
                learnerID,
                assessmentItemID,
                knowledgeTag,
                grade,
                term,
                concept_name,
                chapter_name,
                difficulty_band,
                recommended_level
            FROM gold.vw_personal_item_enriched
            ORDER BY learnerID, assessmentItemID
        """)
        results = cursor.fetchall()
        conn.close()

        if results:
            def safe_decode(value):
                """안전한 문자열 디코딩"""
                if value is None:
                    return None
                if isinstance(value, bytes):
                    try:
                        return value.decode('utf-8')
                    except UnicodeDecodeError:
                        try:
                            return value.decode('cp949')
                        except UnicodeDecodeError:
                            return value.decode('utf-8', errors='ignore')
                return str(value)

            return [
                {
                    'learner_id': result[0],
                    'assessment_item_id': result[1],
                    'knowledge_tag': safe_decode(result[2]),
                    'grade': result[3],
                    'term': result[4],
                    'concept_name': safe_decode(result[5]),
                    'chapter_name': safe_decode(result[6]),
                    'difficulty_band': safe_decode(result[7]),
                    'recommended_level': result[8]
                }
                for result in results
            ]
        return None

    except Exception as e:
        logging.error(f"Error getting sample learner requirements: {str(e)}")
        return None


def get_learner_requirements(learner_id):
    """vw_personal_item_enriched에서 학습자별 문제 요구사항 조회"""
    try:
        conn = get_sql_connection()
        if not conn:
            logging.error("DB 연결 실패")
            return []

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
                recommended_level
            FROM gold.vw_personal_item_enriched
            WHERE learnerID = ?
            ORDER BY assessmentItemID
        """, learner_id)

        results = cursor.fetchall()
        conn.close()

        if results:
            def safe_decode(value):
                """안전한 문자열 디코딩"""
                if value is None:
                    return None
                if isinstance(value, bytes):
                    try:
                        return value.decode('utf-8')
                    except UnicodeDecodeError:
                        try:
                            return value.decode('cp949')
                        except UnicodeDecodeError:
                            return value.decode('utf-8', errors='ignore')
                return str(value)

            requirements = []
            for row in results:
                requirements.append({
                    'learner_id': row[0],
                    'assessment_item_id': row[1],
                    'knowledge_tag': safe_decode(row[2]),
                    'grade': row[3],
                    'term': row[4],
                    'concept_name': safe_decode(row[5]),
                    'chapter_name': safe_decode(row[6]),
                    'difficulty_band': safe_decode(row[7]),
                    'recommended_level': row[8]
                })

            logging.info(f"learnerID {learner_id}: {len(requirements)}개 요구사항 조회")
            return requirements
        else:
            logging.warning(f"learnerID {learner_id}에 대한 데이터 없음")
            return []

    except Exception as e:
        logging.error(f"학습자 요구사항 조회 실패: {str(e)}")
        return []


def generate_question_from_requirement(requirement, client):
    """요구사항 기반 문제 생성"""
    try:
        # 난이도는 원본 그대로 사용
        difficulty = requirement['difficulty_band']

        # AI 문제 생성 (기존 함수 활용)
        question_data = generate_question_with_ai(
            client=client,
            grade=requirement['grade'],
            term=requirement['term'],
            topic_name=requirement['concept_name'],  # concept_name을 topic_name으로 사용
            question_type="선택형",  # 기본값
            difficulty=difficulty,
            existing_questions="",  # 기존 문제 없음
            generated_problems=[]   # 중복 방지 없음
        )

        if question_data and validate_question_format(question_data, "선택형"):
            # 요구사항 메타데이터 추가
            question_data['metadata'] = {
                'assessment_item_id': requirement['assessment_item_id'],
                'knowledge_tag': requirement['knowledge_tag'],
                'grade': requirement['grade'],
                'term': requirement['term'],
                'concept_name': requirement['concept_name'],
                'chapter_name': requirement['chapter_name'],
                'difficulty_band': requirement['difficulty_band'],
                'recommended_level': requirement['recommended_level']
            }

            return question_data
        else:
            logging.warning(f"문제 생성 실패: assessmentItemID {requirement['assessment_item_id']}")
            return None

    except Exception as e:
        logging.error(f"문제 생성 중 오류: {str(e)}")
        return None


def handle_view_generation(req):
    """뷰 기반 개인화 문제 생성 처리 (bulk_generate와 완전 동일)"""
    logging.info('View-based personalized question generation API called')

    try:
        # 샘플 학습자 요구사항 가져오기 (bulk_generate처럼 자동으로)
        requirements = get_sample_learner_requirements(5)
        if not requirements:
            response_data = create_error_response(
                "Failed to get learner requirements from vw_personal_item_enriched",
                status_code=500
            )
            return func.HttpResponse(
                json.dumps(response_data, ensure_ascii=False),
                status_code=500,
                headers={"Content-Type": "application/json; charset=utf-8"}
            )

        print(f"[개인화 생성] 문제 생성 시작 (총 {len(requirements)}개)")
        print("=" * 80)

        client = get_openai_client()
        all_generated_questions = []

        # concept_name별로 생성된 문제들 추적 (중복 방지용)
        concept_generated_problems = {}

        for req_idx, requirement in enumerate(requirements, 1):
            from ..core.utils import get_grade_international
            print(f"\n[요구사항 {req_idx}/{len(requirements)}] learnerID: {requirement['learner_id']}, assessmentItemID: {requirement['assessment_item_id']}")
            print(f"   {get_grade_international(requirement['grade'])} {requirement['term']}학기 - {requirement['concept_name']} (난이도: {requirement['difficulty_band']})")

            # 해당 주제의 기존 문제들 가져오기 (참고용)
            existing_questions = get_question_data("questions", requirement['concept_name'])

            # 같은 concept_name에서 이미 생성된 문제들 가져오기 (중복 방지)
            concept_name = requirement['concept_name']
            generated_problems_for_concept = concept_generated_problems.get(concept_name, [])

            print(f"   📝 {concept_name}: 이미 생성된 문제 {len(generated_problems_for_concept)}개")

            question_data = generate_question_with_ai(
                client, requirement['grade'], requirement['term'], requirement['concept_name'],
                "선택형", requirement['difficulty_band'], existing_questions, generated_problems_for_concept
            )

            if question_data and validate_question_format(question_data, "선택형"):
                # DB에서 미리 매핑된 concept_name 조회
                recommended_concept = get_mapped_concept_name(requirement['concept_name'])
                knowledge_tag = get_knowledge_tag_by_concept(recommended_concept) if recommended_concept else requirement['knowledge_tag']

                # DB 저장 준비 (현재 비활성화)
                question_record = prepare_question_record(
                    requirement['assessment_item_id'], requirement['grade'], requirement['term'], requirement['concept_name'],
                    "선택형", requirement['difficulty_band'], question_data
                )
                answer_record = prepare_answer_record(requirement['assessment_item_id'], question_data)

                # 결과 추가
                question_result = {
                    "assessmentItemID": requirement['assessment_item_id'],  # assessmentItemID 사용
                    **question_data,
                    "metadata": {
                        "assessment_item_id": requirement['assessment_item_id'],
                        "knowledge_tag": requirement['knowledge_tag'],
                        "grade": requirement['grade'],
                        "term": requirement['term'],
                        "concept_name": requirement['concept_name'],
                        "chapter_name": requirement['chapter_name'],
                        "difficulty_band": requirement['difficulty_band'],
                        "recommended_level": requirement['recommended_level'],
                        "source": "vw_personal_item_enriched",
                        "learner_id": requirement['learner_id'],
                        "question_number": req_idx,
                        "mapped_concept_name": recommended_concept,
                        "mapped_knowledge_tag": knowledge_tag
                    }
                }

                all_generated_questions.append(question_result)

                # 생성된 문제를 중복 방지 리스트에 추가
                if concept_name not in concept_generated_problems:
                    concept_generated_problems[concept_name] = []
                concept_generated_problems[concept_name].append(question_data['question_text'][:100])

                print(f"   [성공] {req_idx}/{len(requirements)} - {question_data['question_text'][:50]}...")
                print(f"          원본 concept_name: {requirement['concept_name']}")
                print(f"          매핑된 concept_name: {recommended_concept or '매핑없음'}")
                print(f"          knowledgeTag: {requirement['knowledge_tag']}")
                print(f"   🔄 {concept_name}: 누적 생성 문제 {len(concept_generated_problems[concept_name])}개")
                print()
            else:
                print(f"   [실패] {req_idx}/{len(requirements)} - Question validation failed")

        print("\n" + "=" * 80)
        print(f"[개인화 생성 완료] 총 {len(all_generated_questions)}/{len(requirements)}개 문제")
        print("=" * 80)

        # 요약 정보 생성
        summary = {
            "total_generated": len(all_generated_questions),
            "target_count": len(requirements),
            "requirements_processed": len(requirements)
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
        logging.error(f"Error in view generation: {str(e)}")
        response_data = create_error_response(f"Failed to generate personalized questions: {str(e)}", status_code=500)
        return func.HttpResponse(
            json.dumps(response_data, ensure_ascii=False),
            status_code=500,
            headers={"Content-Type": "application/json; charset=utf-8"}
        )