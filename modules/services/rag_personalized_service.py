# -*- coding: utf-8 -*-
"""
RAG 기반 개인화 문제 생성 서비스
정답률 기반 Top-3 개념 선택 후 6개 문제 생성
"""
import logging
import json
import azure.functions as func
from ..core.database import get_sql_connection, get_question_data, get_mapped_concept_name, get_knowledge_tag_by_concept
from ..core.ai_service import get_openai_client, generate_question_with_ai
from ..core.validation import validate_question_format, prepare_question_record, prepare_answer_record
from ..core.utils import generate_question_id, get_grade_international
from ..core.responses import create_success_response, create_error_response


def get_top_concepts_by_accuracy(grade, top_k=3):
    """정답률 기반으로 Top-K 개념 선택 (0.55~0.70 범위에서 가까운 순)"""
    try:
        print(f"      Connecting to database...")
        conn = get_sql_connection()
        if not conn:
            print(f"      Database connection failed!")
            return None

        cursor = conn.cursor()
        print(f"      Executing query for grade={grade} (all terms)...")

        # 1단계: 전체 레코드 수 확인
        cursor.execute("SELECT COUNT(*) FROM gold.vw_personal_item_enriched")
        total_count = cursor.fetchone()[0]
        print(f"      Total records in view: {total_count}")

        # 2단계: grade=8 데이터 확인
        cursor.execute(f"SELECT COUNT(*) FROM gold.vw_personal_item_enriched WHERE grade = {grade}")
        grade_count = cursor.fetchone()[0]
        print(f"      Grade {grade} records: {grade_count}")

        # 3단계: 샘플 데이터 확인 (concept_name 명시적 캐스팅)
        if grade_count > 0:
            try:
                cursor.execute(f"SELECT TOP 3 CAST(concept_name AS NVARCHAR(MAX)) as concept_name, is_correct FROM gold.vw_personal_item_enriched WHERE grade = {grade}")
                sample_data = cursor.fetchall()
                print(f"      Sample data:")
                for i, (concept, is_correct) in enumerate(sample_data):
                    print(f"         {i+1}. {concept} | is_correct: {is_correct}")
            except Exception as e:
                print(f"      Sample data query failed: {str(e)}")

        # 4단계: 메인 쿼리 실행 (nvarchar 명시적 캐스팅)
        try:
            query = f"""
                SELECT
                    CAST(concept_name AS NVARCHAR(MAX)) as concept_name,
                    AVG(CAST(is_correct AS FLOAT)) as avg_correct_rate,
                    COUNT(*) as item_count
                FROM gold.vw_personal_item_enriched
                WHERE grade = {grade}
                GROUP BY concept_name
                HAVING COUNT(*) >= 1
                ORDER BY ABS(AVG(CAST(is_correct AS FLOAT)) - 0.625) ASC
            """
            print(f"      Executing main query (with NVARCHAR casting)...")

            cursor.execute(query)
            results = cursor.fetchall()
            print(f"      Raw query results: {len(results)} rows")

            if results:
                print(f"      Sample results (first 3):")
                for i, result in enumerate(results[:3]):
                    print(f"         {i+1}. {result[0]} (rate: {result[1]:.3f}, count: {result[2]})")

            conn.close()

            if results:
                concepts = []
                for result in results:
                    concepts.append({
                        'concept_name': result[0],
                        'avg_correct_rate': result[1],
                        'item_count': result[2]
                    })

                # Top-K 개념 반환
                return concepts[:top_k] if len(concepts) >= top_k else concepts

            return []

        except Exception as e:
            print(f"      Main query failed: {str(e)}")
            conn.close()
            return []

    except Exception as e:
        logging.error(f"Error getting top concepts by accuracy: {str(e)}")
        return None


def get_assessment_ids_by_concepts(concepts, target_count=6):
    """개념별 assessmentItemID 수집 및 6개 확정"""
    try:
        conn = get_sql_connection()
        if not conn:
            return None

        cursor = conn.cursor()
        all_ids = []

        # 각 개념별 ID 수집
        for concept in concepts:
            concept_name = concept['concept_name']

            # 테스트용으로 2학년 전체 (학기 조건 제거)
            cursor.execute("""
                SELECT DISTINCT
                    assessmentItemID,
                    concept_name,
                    grade,
                    term,
                    unit_name,
                    chapter_name,
                    difficulty_band,
                    knowledgeTag
                FROM gold.vw_personal_item_enriched
                WHERE concept_name = ? AND grade = 8
                ORDER BY assessmentItemID
            """, (concept_name,))

            results = cursor.fetchall()

            for result in results:
                all_ids.append({
                    'assessment_item_id': result[0],
                    'concept_name': result[1],
                    'grade': result[2],
                    'term': result[3],
                    'unit_name': result[4],
                    'chapter_name': result[5],
                    'difficulty_band': result[6],
                    'knowledge_tag': result[7]
                })

        conn.close()

        # ID 개수 조정
        if len(all_ids) == target_count:
            # 딱 맞는 경우
            return all_ids
        elif len(all_ids) < target_count:
            # 부족한 경우 - 추가 개념에서 보충
            return get_additional_ids(all_ids, target_count - len(all_ids))
        else:
            # 초과하는 경우 - 각 개념별 균등 샘플링
            return balance_ids_by_concept(all_ids, target_count)

    except Exception as e:
        logging.error(f"Error getting assessment IDs by concepts: {str(e)}")
        return None


def get_additional_ids(existing_ids, needed_count):
    """부족분을 하위 개념에서 보충"""
    try:
        conn = get_sql_connection()
        if not conn:
            return existing_ids

        cursor = conn.cursor()

        # 이미 사용된 개념 제외
        used_concepts = set(item['concept_name'] for item in existing_ids)
        concept_filter = "'" + "','".join(used_concepts) + "'" if used_concepts else "''"

        # 테스트용으로 2학년 전체 (학기 조건 제거), 하위 순위 개념에서 필요한 만큼 가져오기
        cursor.execute(f"""
            SELECT TOP {needed_count}
                assessmentItemID,
                concept_name,
                grade,
                term,
                unit_name,
                chapter_name,
                difficulty_band,
                knowledgeTag
            FROM gold.vw_personal_item_enriched
            WHERE grade = 8
            AND concept_name NOT IN ({concept_filter})
            ORDER BY assessmentItemID
        """)

        results = cursor.fetchall()
        conn.close()

        for result in results:
            existing_ids.append({
                'assessment_item_id': result[0],
                'concept_name': result[1],
                'grade': result[2],
                'term': result[3],
                'unit_name': result[4],
                'chapter_name': result[5],
                'difficulty_band': result[6],
                'knowledge_tag': result[7]
            })

        return existing_ids

    except Exception as e:
        logging.error(f"Error getting additional IDs: {str(e)}")
        return existing_ids


def balance_ids_by_concept(all_ids, target_count):
    """개념별 균등 샘플링으로 6개 맞춤"""
    from collections import defaultdict
    import math

    # 개념별 그룹화
    concept_groups = defaultdict(list)
    for item in all_ids:
        concept_groups[item['concept_name']].append(item)

    balanced_ids = []
    concepts = list(concept_groups.keys())
    items_per_concept = target_count // len(concepts)
    remaining = target_count % len(concepts)

    for i, concept in enumerate(concepts):
        concept_items = concept_groups[concept]

        # 각 개념별 할당량 계산
        take_count = items_per_concept
        if i < remaining:  # 나머지를 앞쪽 개념들에 분배
            take_count += 1

        # 해당 개념에서 필요한 만큼 선택
        balanced_ids.extend(concept_items[:take_count])

        if len(balanced_ids) >= target_count:
            break

    return balanced_ids[:target_count]


def create_rag_context_block(assessment_items):
    """RAG 컨텍스트 블록 생성"""
    context_lines = ["불변 목록 (각 행당 정확히 1문항 생성):"]

    for i, item in enumerate(assessment_items, 1):
        line = f"[{i}] ID={item['assessment_item_id']}, concept={item['concept_name']}, grade=중{item['grade']}, term={item['term']}학기"
        if item.get('unit_name'):
            line += f", unit={item['unit_name']}"
        context_lines.append(line)

    context_lines.extend([
        "",
        "정책 (필수 준수):",
        "- 각 행당 정확히 1문항, 동일 ID/동일 주제 유지",
        "- 객관식 4지, 한국어, LaTeX 허용",
        "- assessmentItemID와 concept_name 변경 금지",
        "- 개념 밖 지식 사용 금지, 근거 부족 시 해당 행은 skip:true",
        "- 6개를 한 번에 JSON 배열로 반환 (길이 6, skip 포함 가능)"
    ])

    return "\n".join(context_lines)


def handle_rag_personalized_generation(req):
    """RAG 기반 개인화 문제 생성 처리"""
    logging.info('RAG personalized question generation API called')

    try:
        # 테스트용으로 2학년 전체 (국제식: 중2=8, 학기 조건 제거)
        grade = 8  # 중학교 2학년 = 8 (int 타입)

        print(f"\n[RAG Process Start] Grade {grade} (All Terms)")
        print(f"[Step 1] Retrieval - Concept Selection by Accuracy")
        logging.info(f"Using fixed parameters: grade={grade}")

        # 1단계: 정답률 기반 Top-3 개념 선택
        print(f"   Querying database for concepts...")
        top_concepts = get_top_concepts_by_accuracy(grade, top_k=3)

        print(f"   Database query result: {len(top_concepts) if top_concepts else 0} concepts found")
        if top_concepts:
            print(f"   Found concepts: {[c['concept_name'] for c in top_concepts]}")
        else:
            print(f"   No concepts found - checking database connection and data...")

        if not top_concepts:
            response_data = create_error_response(
                "적절한 개념을 찾을 수 없습니다.",
                status_code=404
            )
            return func.HttpResponse(
                json.dumps(response_data, ensure_ascii=False),
                status_code=404,
                headers={"Content-Type": "application/json; charset=utf-8"}
            )

        print(f"   Selected concepts ({len(top_concepts)} found):")
        for i, concept in enumerate(top_concepts, 1):
            print(f"      {i}. {concept['concept_name']} (accuracy: {concept['avg_correct_rate']:.3f})")
        logging.info(f"Selected top concepts: {[c['concept_name'] for c in top_concepts]}")

        print(f"[Step 2] Assessment ID Collection (Target: 6 IDs)")
        # 2단계: 각 개념별 assessmentItemID 수집 및 6개 확정
        assessment_items = get_assessment_ids_by_concepts(top_concepts, target_count=6)
        if not assessment_items or len(assessment_items) == 0:
            response_data = create_error_response(
                "문제 생성을 위한 데이터를 찾을 수 없습니다.",
                status_code=404
            )
            return func.HttpResponse(
                json.dumps(response_data, ensure_ascii=False),
                status_code=404,
                headers={"Content-Type": "application/json; charset=utf-8"}
            )

        print(f"   └─ 확정된 Assessment ID ({len(assessment_items)}개):")
        for i, item in enumerate(assessment_items, 1):
            print(f"      {i}. {item['assessment_item_id']} - {item['concept_name']}")
        logging.info(f"Selected {len(assessment_items)} assessment items")

        print(f"[3단계] Augmentation - RAG 컨텍스트 블록 생성")
        # 3단계: RAG 컨텍스트 블록 생성
        context_block = create_rag_context_block(assessment_items)
        print(f"   └─ 생성된 컨텍스트 블록:")
        context_lines = context_block.split('\n')
        for line in context_lines[:8]:  # 처음 8줄만 출력
            print(f"      {line}")
        if len(context_lines) > 8:
            total_lines = len(context_lines)
            print(f"      ... (총 {total_lines}줄)")
        logging.info(f"Generated context block with {len(assessment_items)} items")

        print(f"[4단계] Generation - AI 문제 생성")
        # 4단계: AI 문제 생성 (RAG 프롬프트 사용)
        client = get_openai_client()
        if not client:
            print(f"   [오류] OpenAI 클라이언트 연결 실패")
            response_data = create_error_response(
                "OpenAI client connection failed",
                status_code=500
            )
            return func.HttpResponse(
                json.dumps(response_data, ensure_ascii=False),
                status_code=500,
                headers={"Content-Type": "application/json; charset=utf-8"}
            )

        print(f"   RAG 전용 프롬프트로 {len(assessment_items)}개 문제 생성 요청...")
        # RAG 전용 프롬프트로 문제 생성
        generated_questions = generate_rag_questions_with_ai(client, context_block, assessment_items)

        if not generated_questions:
            print(f"   [오류] AI 문제 생성 실패")
            response_data = create_error_response(
                "문제 생성에 실패했습니다.",
                status_code=500
            )
            return func.HttpResponse(
                json.dumps(response_data, ensure_ascii=False),
                status_code=500,
                headers={"Content-Type": "application/json; charset=utf-8"}
            )

        print(f"   [성공] 성공적으로 {len(generated_questions)}개 문제 생성 완료")
        print(f"[RAG 프로세스 완료] 총 {len(generated_questions)}개 객관식 문제 반환\n")

        # 성공 응답 생성
        concepts_used = len(set(item['concept_name'] for item in assessment_items))

        response_data = create_success_response(
            generated_questions,
            additional_data={
                "total_generated": len(generated_questions),
                "concepts_used": concepts_used,
                "retrieval_strategy": "top3_with_backup",
                "target_accuracy_range": "0.55-0.70"
            }
        )

        return func.HttpResponse(
            json.dumps(response_data, ensure_ascii=False),
            status_code=200,
            headers={"Content-Type": "application/json; charset=utf-8"}
        )

    except Exception as e:
        logging.error(f"RAG personalized generation error: {str(e)}")

        response_data = create_error_response(
            f"내부 서버 오류: {str(e)}",
            status_code=500
        )
        return func.HttpResponse(
            json.dumps(response_data, ensure_ascii=False),
            status_code=500,
            headers={"Content-Type": "application/json; charset=utf-8"}
        )


def generate_rag_questions_with_ai(client, context_block, assessment_items):
    """RAG 전용 AI 문제 생성"""
    try:
        # RAG 전용 시스템 프롬프트
        system_prompt = """당신은 한국 중학교 수학 문제 생성 전문가입니다.
주어진 불변 목록의 각 행에 대해 정확히 1문항씩 생성해야 합니다.

절대 준수 규칙:
1. 모든 문제는 반드시 객관식 4지 선택형으로 생성 (①②③④)
2. assessmentItemID와 concept_name은 입력과 동일해야 하며, 절대 변경하지 마세요
3. 각 개념의 범위를 벗어나는 지식은 사용하지 마세요
4. 근거가 부족한 경우 해당 행은 "skip": true로 표시하세요
5. 한국어로 작성하고, 필요시 LaTeX를 사용하세요
6. 서술형, 단답형, 빈칸형 등은 절대 생성하지 마세요 - 오직 객관식만!

JSON 출력 형식:
[
  {
    "assessmentItemID": "입력과 동일한 ID",
    "concept_name": "입력과 동일한 개념명",
    "question_text": "문제 내용",
    "choices": ["① ...", "② ...", "③ ...", "④ ..."],
    "answer": "①",
    "explanation": "풀이 설명",
    "skip": false
  }
]
"""

        user_prompt = f"""다음 불변 목록을 기반으로 문제를 생성해주세요:

{context_block}

각 행에 대해 정확히 1문항씩, 총 {len(assessment_items)}개의 문제를 JSON 배열로 반환해주세요."""

        print(f"      OpenAI GPT-4 모델 호출 중...")
        response = client.chat.completions.create(
            model="gpt-4o-create_question",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
            max_tokens=4000
        )

        ai_response = response.choices[0].message.content.strip()
        print(f"      AI 응답 수신 완료 (길이: {len(ai_response)} 문자)")
        logging.info(f"AI Response received, length: {len(ai_response)}")

        # JSON 파싱 시도
        try:
            # 코드 블록이 있다면 제거
            if "```json" in ai_response:
                ai_response = ai_response.split("```json")[1].split("```")[0].strip()
            elif "```" in ai_response:
                ai_response = ai_response.split("```")[1].strip()

            parsed_questions = json.loads(ai_response)

            if not isinstance(parsed_questions, list):
                print(f"      [오류] AI 응답이 리스트 형식이 아닙니다")
                logging.error("AI response is not a list")
                return None

            print(f"      JSON 파싱 성공, {len(parsed_questions)}개 문제 파싱됨")

            # 결과 처리 및 ID 추가
            final_questions = []
            for i, question in enumerate(parsed_questions):
                if question.get('skip', False):
                    print(f"      [주의] 문제 {i+1}번이 AI에 의해 스킵됨")
                    logging.warning(f"Question {i+1} was skipped by AI")
                    continue

                # 객관식 형식 검증
                if not question.get('choices') or len(question.get('choices', [])) != 4:
                    print(f"      [주의] 문제 {i+1}번: 객관식 4지 형식이 아님, 스킵")
                    continue

                # question_id 추가
                question['id'] = generate_question_id()

                # 메타데이터 추가
                if i < len(assessment_items):
                    item = assessment_items[i]
                    question['metadata'] = {
                        'grade': item['grade'],
                        'term': item['term'],
                        'concept_name': item['concept_name'],
                        'chapter_name': item.get('chapter_name', ''),
                        'difficulty_band': item.get('difficulty_band', '중'),
                        'knowledge_tag': item.get('knowledge_tag', ''),
                        'unit_name': item.get('unit_name', '')
                    }

                print(f"      [완료] 문제 {i+1}번: {question.get('concept_name', '?')} (ID: {question['id'][:8]}...)")
                final_questions.append(question)

            print(f"      최종 {len(final_questions)}개 객관식 문제 검증 완료")
            logging.info(f"Successfully generated {len(final_questions)} questions")
            return final_questions

        except json.JSONDecodeError as e:
            print(f"      [오류] JSON 파싱 오류: {str(e)}")
            logging.error(f"JSON parsing error: {str(e)}")
            logging.error(f"Raw AI response: {ai_response[:500]}...")
            return None

    except Exception as e:
        logging.error(f"Error generating RAG questions with AI: {str(e)}")
        return None