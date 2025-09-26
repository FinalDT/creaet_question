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


def create_cors_headers():
    """CORS 헤더 생성 (3000포트만 허용)"""
    return {
        "Content-Type": "application/json; charset=utf-8",
        "Access-Control-Allow-Origin": "http://localhost:3000",
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization"
    }


def extract_primary_chapter(chapter_name):
    """chapter_name에서 첫 번째 주제 추출
    예: '이차방정식 > 이차방정식 > 제곱근을 이용한 이차방정식의 풀이' → '이차방정식'
    """
    if not chapter_name:
        return chapter_name

    # '>' 구분자로 분리하여 첫 번째 부분 추출
    parts = chapter_name.split('>')
    return parts[0].strip() if parts else chapter_name


def get_concept_difficulty_band(concept_name):
    """개념명 기반 난이도 판단 (임시 해결책)"""
    if not concept_name:
        return "중"
    
    concept_lower = concept_name.lower()
    
    # 고난이도 개념 키워드
    high_difficulty_keywords = [
        '이차방정식', '이차함수', '삼각함수', '미분', '적분', '확률과통계',
        '벡터', '행렬', '극한', '로그', '지수', '삼각비', '원의방정식',
        '포물선', '타원', '쌍곡선', '공간도형', '입체도형', '회전체',
        '조합', '순열', '이항정리', '확률분포', '정규분포'
    ]
    
    # 저난이도 개념 키워드  
    low_difficulty_keywords = [
        '자연수', '정수', '유리수', '무리수', '소수', '분수',
        '덧셈', '뺄셈', '곱셈', '나눗셈', '사칙연산', '계산',
        '기본도형', '점', '선', '면', '각', '직선', '반직선', '선분',
        '원', '삼각형', '사각형', '다각형', '대칭', '이동',
        '표', '그래프', '막대그래프', '원그래프', '평균', '중앙값'
    ]
    
    # 고난이도 체크
    for keyword in high_difficulty_keywords:
        if keyword in concept_lower:
            return "상"
    
    # 저난이도 체크
    for keyword in low_difficulty_keywords:
        if keyword in concept_lower:
            return "하"
    
    # 기본값 (중간 난이도)
    return "중"


def get_top_concepts_by_accuracy(grade, top_k=3):
    """정답률 기반으로 Top-K 개념 선택 (chapter_name 첫 번째 부분 기준)"""
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
                WITH primary_chapters AS (
                    SELECT
                        CASE
                            WHEN CHARINDEX('>', CAST(chapter_name AS NVARCHAR(MAX))) > 0
                            THEN LTRIM(RTRIM(SUBSTRING(CAST(chapter_name AS NVARCHAR(MAX)), 1, CHARINDEX('>', CAST(chapter_name AS NVARCHAR(MAX))) - 1)))
                            ELSE CAST(chapter_name AS NVARCHAR(MAX))
                        END as primary_chapter,
                        CAST(is_correct AS FLOAT) as is_correct
                    FROM gold.vw_personal_item_enriched
                    WHERE grade = {grade}
                )
                SELECT
                    primary_chapter,
                    AVG(is_correct) as avg_correct_rate,
                    COUNT(*) as item_count
                FROM primary_chapters
                WHERE primary_chapter IS NOT NULL AND primary_chapter != ''
                GROUP BY primary_chapter
                HAVING COUNT(*) >= 1
                ORDER BY ABS(AVG(is_correct) - 0.625) ASC
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
                        'primary_chapter': result[0],  # chapter_name 첫 번째 부분
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

        # 각 primary chapter별 ID 수집
        for concept in concepts:
            primary_chapter = concept['primary_chapter']

            # chapter_name이 해당 primary chapter로 시작하는 레코드들 조회
            cursor.execute("""
                SELECT DISTINCT
                    assessmentItemID,
                    concept_name,
                    grade,
                    term,
                    chapter_name
                FROM gold.vw_personal_item_enriched
                WHERE grade = 8
                  AND (
                      CAST(chapter_name AS NVARCHAR(MAX)) LIKE ? + ' > %'
                      OR CAST(chapter_name AS NVARCHAR(MAX)) = ?
                  )
                ORDER BY assessmentItemID
            """, (primary_chapter, primary_chapter))

            results = cursor.fetchall()

            for result in results:
                all_ids.append({
                    'assessment_item_id': result[0],
                    'concept_name': result[1],
                    'grade': result[2],
                    'term': result[3],
                    'chapter_name': result[4]
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
                chapter_name
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
                'chapter_name': result[4]
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


def find_matching_assessment_id(question, assessment_items):
    """생성된 문제의 주제에 맞는 assessmentItemID 찾기"""
    question_text = question.get('question_text', '').lower()

    # 키워드 기반 매칭
    concept_keywords = {
        '이차방정식': ['이차방정식', 'x²', 'x^2', '근', '해'],
        '평행사변형': ['평행사변형', '평행선', '대각'],
        '유한소수': ['소수', '분수', '0.', '유한'],
        '연립방정식': ['연립', '방정식', '{', '}'],
        '삼각형': ['삼각형', '외심', '내심', '각'],
        '일차함수': ['일차함수', 'y =', 'x축', 'y축', '그래프']
    }

    # 각 assessment_item과 매칭 시도
    for item in assessment_items:
        concept_name = item['concept_name']

        # concept_name과 직접 비교
        if any(keyword in question_text for keyword in concept_keywords.get(concept_name.split()[0], [])):
            return item['assessment_item_id']

    # 매칭 실패 시 첫번째 항목 반환 (fallback)
    return assessment_items[0]['assessment_item_id'] if assessment_items else generate_question_id()


def create_rag_context_block(assessment_items):
    """RAG 컨텍스트 블록 생성"""
    context_lines = ["불변 목록 (각 행당 정확히 1문항 생성):"]

    for i, item in enumerate(assessment_items, 1):
        # difficulty_band가 없거나 NULL인 경우 개념 기반 난이도 할당
        db_difficulty = item.get('difficulty_band')
        if not db_difficulty or db_difficulty == '중':
            difficulty_band = get_concept_difficulty_band(item['concept_name'])
        else:
            difficulty_band = db_difficulty
            
        line = f"[{i}] ID={item['assessment_item_id']}, concept={item['concept_name']}, chapter={item['chapter_name']}, grade=중{item['grade']-6}, term={item['term']}학기, difficulty={difficulty_band}"
        context_lines.append(line)

    context_lines.extend([
        "",
        "정책 (필수 준수):",
        "- 각 행당 정확히 1문항, 동일 ID/동일 주제 유지",
        "- 객관식 4지, 한국어, LaTeX 허용",
        "- assessmentItemID와 concept_name 변경 금지",
        "- 개념 밖 지식 사용 금지, 근거 부족 시 해당 행은 skip:true",
        "- 난이도는 difficulty 정보를 참고하여 적절한 수준으로 생성 (상/중/하)",
        "- 6개를 한 번에 JSON 배열로 반환 (길이 6, skip 포함 가능)"
    ])

    return "\n".join(context_lines)


def handle_rag_personalized_generation(req):
    """RAG 기반 개인화 문제 생성 처리"""
    logging.info('RAG personalized question generation API called')

    try:
        # 프론트엔드에서 전달받은 학년 파라미터 처리
        grade_param = None
        
        # GET 요청: URL 파라미터에서 추출
        if req.method == "GET":
            grade_param = req.params.get('grade')
        # POST 요청: JSON body 또는 URL 파라미터에서 추출
        elif req.method == "POST":
            try:
                req_body = req.get_json()
                if req_body and 'grade' in req_body:
                    grade_param = req_body.get('grade')
                else:
                    grade_param = req.params.get('grade')
            except:
                grade_param = req.params.get('grade')
        
        # 학년 파라미터 검증
        if not grade_param:
            response_data = create_error_response(
                "학년 파라미터가 필요합니다. 예: ?grade=2",
                status_code=400
            )
            return func.HttpResponse(
                json.dumps(response_data, ensure_ascii=False),
                status_code=400,
                headers=create_cors_headers()
            )
        
        try:
            grade_korean = int(grade_param)
        except ValueError:
            response_data = create_error_response(
                "학년은 숫자여야 합니다. 지원 학년: 1, 2, 3 (중학교)",
                status_code=400
            )
            return func.HttpResponse(
                json.dumps(response_data, ensure_ascii=False),
                status_code=400,
                headers=create_cors_headers()
            )
        
        # 학년 범위 검증 (중학교 1-3학년)
        if grade_korean not in [1, 2, 3]:
            response_data = create_error_response(
                "지원되지 않는 학년입니다. 지원 학년: 1, 2, 3 (중학교)",
                status_code=400
            )
            return func.HttpResponse(
                json.dumps(response_data, ensure_ascii=False),
                status_code=400,
                headers=create_cors_headers()
            )
        
        # 한국식 학년 → 국제식 학년 변환 (1,2,3 → 7,8,9)
        grade = grade_korean + 6
        
        print(f"\n[RAG Process Start] Grade {grade} (중학교 {grade_korean}학년, All Terms)")
        print(f"[Step 1] Retrieval - Concept Selection by Accuracy")
        logging.info(f"Using parameters: korean_grade={grade_korean}, international_grade={grade}")

        # 1단계: 정답률 기반 Top-3 개념 선택
        print(f"   Querying database for concepts...")
        top_concepts = get_top_concepts_by_accuracy(grade, top_k=3)

        print(f"   Database query result: {len(top_concepts) if top_concepts else 0} concepts found")
        if top_concepts:
            print(f"   Found concepts: {[c['primary_chapter'] for c in top_concepts]}")
        else:
            print(f"   No concepts found - checking database connection and data...")

        if not top_concepts:
            response_data = create_error_response(
                f"중학교 {grade_korean}학년에 대한 학습 데이터를 찾을 수 없습니다. 다른 학년을 시도해보세요. (지원 학년: 1, 2, 3)",
                status_code=404
            )
            return func.HttpResponse(
                json.dumps(response_data, ensure_ascii=False),
                status_code=404,
                headers=create_cors_headers()
            )

        print(f"   Selected concepts ({len(top_concepts)} found):")
        for i, concept in enumerate(top_concepts, 1):
            print(f"      {i}. {concept['primary_chapter']} (accuracy: {concept['avg_correct_rate']:.3f})")
        logging.info(f"Selected top concepts: {[c['primary_chapter'] for c in top_concepts]}")

        print(f"[Step 2] Assessment ID Collection (Target: 6 IDs)")
        # 2단계: 각 개념별 assessmentItemID 수집 및 6개 확정
        assessment_items = get_assessment_ids_by_concepts(top_concepts, target_count=6)
        if not assessment_items or len(assessment_items) == 0:
            response_data = create_error_response(
                f"중학교 {grade_korean}학년의 문제 생성 데이터가 부족합니다. 다른 학년을 시도해보세요.",
                status_code=404
            )
            return func.HttpResponse(
                json.dumps(response_data, ensure_ascii=False),
                status_code=404,
                headers=create_cors_headers()
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
                headers=create_cors_headers()
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
                headers=create_cors_headers()
            )

        print(f"   [성공] 성공적으로 {len(generated_questions)}개 문제 생성 완료")
        print(f"[RAG 프로세스 완료] 총 {len(generated_questions)}개 객관식 문제 반환\n")

        # 성공 응답 생성
        concepts_used = len(set(item['concept_name'] for item in assessment_items))

        response_data = create_success_response({
            "success": True,
            "generated_questions": generated_questions,
            "total_generated": len(generated_questions),
            "concepts_used": concepts_used,
            "grade_info": {
                "korean_grade": grade_korean,
                "international_grade": grade,
                "grade_description": f"중학교 {grade_korean}학년"
            },
            "retrieval_strategy": "top3_with_backup",
            "target_accuracy_range": "0.55-0.70",
            "validation": {
                "format_check": "passed",
                "db_storage": "disabled_for_testing"
            }
        })

        return func.HttpResponse(
            json.dumps(response_data, ensure_ascii=False),
            status_code=200,
            headers=create_cors_headers()
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
            headers=create_cors_headers()
        )


def generate_rag_questions_with_ai(client, context_block, assessment_items):
    """RAG 전용 AI 문제 생성"""
    try:
        # 도형/그래프 관련 개념 확인 (SVG 필요 여부 판단)
        concept_names = [item['concept_name'] for item in assessment_items]
        all_concepts = ' '.join(concept_names).lower()

        requires_svg = any(keyword in all_concepts for keyword in [
            '도형', '삼각형', '사각형', '원', '다각형', '기하',
            '그래프', '좌표', '직선',
            '통계', '차트', '막대', '원그래프', '히스토그램',
            '각', '넓이', '부피', '길이', '거리', '평행선', '수직선'
        ])

        print(f"      [SVG 감지] 도형/그래프 관련 개념 감지: {'Yes' if requires_svg else 'No'}")
        if requires_svg:
            print(f"      [SVG 감지] 관련 개념: {concept_names}")

        # SVG 관련 지침
        if requires_svg:
            svg_instructions = """

🔴 **SVG 필수 생성**: 이 개념들은 도형/그래프 관련이므로 SVG가 반드시 필요합니다!

**문제-그림 완벽 일치 원칙**:
1. 문제에서 언급하는 모든 점, 변, 각을 SVG에 정확히 표시
2. 문제에서 사용하는 기호/이름을 SVG에 동일하게 라벨링
3. 문제에서 주어진 수치나 각도를 SVG에 반드시 표시
4. 문제 상황과 100% 일치하는 도형/그래프 그리기

**구체적 지침**:
- 점: 문제에서 "점 A, B, C"라고 하면 SVG에서 정확히 A, B, C로 라벨링
- 각: 문제에서 "∠A, ∠B"라고 하면 SVG에서 해당 각에 각도 표시선과 라벨
- 변: 문제에서 "변 AB"라고 하면 SVG에서 AB 변을 명확히 표시
- 수치: 문제에서 "5cm, 60°"라고 하면 SVG에서 해당 위치에 수치 표시

다음 유형에 맞는 SVG를 생성하세요:
- 도형: 삼각형, 사각형, 원 등의 정확한 도형 그리기
- 그래프: 좌표평면, 함수 그래프, 직선/곡선
- 통계: 막대그래프, 원그래프, 히스토그램
- 기하: 각도, 길이, 넓이 표시

SVG 사양 (태블릿 최적화):
- 뷰박스 사용: viewBox='0 0 400 300' width='100%' height='auto'
- 스타일: 검은색 선(stroke='#000' stroke-width='2'), 회색 채우기(fill='#f0f0f0')
- 텍스트: font-family='Arial' font-size='16' (태블릿용 크기)
- 격자, 축, 수치, 라벨 명확히 표시

🔴 **중요**: SVG 속성값에는 반드시 단일 인용부호(')를 사용하세요!

**각도 표현 규칙**:
- 각도를 시각적으로 그리지 마세요 (호나 부채꼴 금지)
- 대신 각의 꼭짓점과 두 변만 그리고 알파벳으로 표시
- 예: ∠ABC는 점 A, B, C만 표시하고 "∠ABC" 텍스트 라벨 사용

**절대 금지**: svg_content를 null로 설정하지 마세요!
**필수**: 문제 내용과 완벽히 일치하는 그림만 생성하세요!
"""
        else:
            svg_instructions = """

SVG 생성 판단:
- 순수 계산/대수 문제: svg_content를 null로 설정
- 시각적 요소가 조금이라도 있으면: SVG 생성

SVG 사양 (필요한 경우):
- 뷰박스 사용: viewBox='0 0 300 200' width='100%' height='auto'
- 스타일: 검은색 선(stroke='#000' stroke-width='2'), 회색 채우기(fill='#f0f0f0')
- 텍스트: font-family='Arial' font-size='14'

🔴 **중요**: SVG 속성값에는 반드시 단일 인용부호(')를 사용하세요!
"""

        # RAG 전용 시스템 프롬프트
        system_prompt = f"""당신은 한국 중학교 수학 문제 생성 전문가입니다.
주어진 불변 목록의 각 행에 대해 정확히 1문항씩 생성해야 합니다.

절대 준수 규칙:
1. 모든 문제는 반드시 객관식 4지 선택형으로 생성 (①②③④)
2. assessmentItemID와 concept_name은 입력과 동일해야 하며, 절대 변경하지 마세요
3. 각 개념의 범위를 벗어나는 지식은 사용하지 마세요
4. 근거가 부족한 경우 해당 행은 "skip": true로 표시하세요
5. 한국어로 작성하고, 필요시 LaTeX를 사용하세요
6. 서술형, 단답형, 빈칸형 등은 절대 생성하지 마세요 - 오직 객관식만!

{svg_instructions}

JSON 출력 형식:
[
  {{
    "assessmentItemID": "입력과 동일한 ID",
    "concept_name": "입력과 동일한 개념명",
    "question_text": "문제 내용",
    "choices": ["① ...", "② ...", "③ ...", "④ ..."],
    "answer": "①",
    "explanation": "풀이 설명",
    "svg_content": "SVG 코드 또는 null",
    "skip": false
  }}
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

            # LaTeX 백슬래시 이스케이프 처리 (API 4번과 동일한 로직 + 디버깅 강화)
            import re

            print(f"      [디버그] 원본 AI 응답 길이: {len(ai_response)} 문자")
            print(f"      [디버그] 응답 일부 확인: {ai_response[:200]}...")

            def fix_latex_backslashes(content):
                print(f"      [디버그] LaTeX 처리 시작, 입력 길이: {len(content)}")

                # 1. 먼저 단일 백슬래시 패턴들을 찾아서 처리 (로그에서 본 \( 같은 패턴)
                single_backslash_patterns = [
                    r'\\(\()', r'\\(\))',  # \( \)
                    r'\\(overline)', r'\\(underline)',  # \overline \underline
                    r'\\(frac)', r'\\(sqrt)', r'\\(text)', r'\\(mathrm)',  # 기본 명령어들
                    r'\\(left)', r'\\(right)', r'\\(times)', r'\\(cdot)',
                    r'\\(pi)', r'\\(alpha)', r'\\(beta)', r'\\(gamma)', r'\\(theta)',
                    r'\\(phi)', r'\\(lambda)', r'\\(delta)', r'\\(omega)', r'\\(sigma)'
                ]

                single_backslash_count = 0
                for pattern in single_backslash_patterns:
                    matches = re.findall(pattern, content)
                    if matches:
                        print(f"      [디버그] 단일 백슬래시 패턴 발견: {pattern} - {len(matches)}개")
                        single_backslash_count += len(matches)
                    # 단일 백슬래시를 이중 백슬래시로 변경
                    content = re.sub(pattern, r'\\\\\\1', content)

                # 2. LaTeX 명령어들을 정확하게 이스케이프 (확장된 목록)
                latex_commands = [
                    'frac', 'sqrt', 'text', 'mathrm', 'times', 'cdot', 'pi', 'alpha', 'beta', 'gamma',
                    'theta', 'phi', 'lambda', 'delta', 'omega', 'sigma', 'mu', 'nu', 'tau',
                    'left', 'right', 'big', 'Big', 'bigg', 'Bigg', 'overline', 'underline'
                ]

                # 처리된 명령어 카운트
                processed_count = single_backslash_count
                for cmd in latex_commands:
                    matches = re.findall(f'\\\\\\\\{cmd}\\b', content)
                    if matches:
                        print(f"      [디버그] LaTeX 명령어 '{cmd}' 발견: {len(matches)}개")
                        processed_count += len(matches)
                    # \\cmd 패턴을 찾아서 \\\\cmd로 변경
                    content = re.sub(f'\\\\\\\\{cmd}\\b', f'\\\\\\\\\\\\\\\\{cmd}', content)

                # LaTeX 괄호 구조 처리
                bracket_matches = re.findall(r'\\\\(\(|\)|\[|\]|\{|\})', content)
                if bracket_matches:
                    print(f"      [디버그] LaTeX 괄호 발견: {len(bracket_matches)}개")
                content = re.sub(r'\\\\(\(|\)|\[|\]|\{|\})', r'\\\\\\\\\\1', content)

                # 과도한 백슬래시 정리 (8개 이상 → 4개)
                excessive_backslashes = re.findall(r'\\{8,}', content)
                if excessive_backslashes:
                    print(f"      [디버그] 과도한 백슬래시 발견: {len(excessive_backslashes)}개")
                content = re.sub(r'\\{8,}', r'\\\\\\\\', content)

                print(f"      [디버그] LaTeX 처리 완료, 총 {processed_count}개 명령어 처리됨")
                return content

            # 전체 JSON 내용 처리
            safe_json_content = ai_response

            # SVG 속성의 이중 인용부호를 단일 인용부호로 변경
            svg_matches = re.findall(r'([a-zA-Z-]+)="([^"]*)"', safe_json_content)
            if svg_matches:
                print(f"      [디버그] SVG 속성 발견: {len(svg_matches)}개")
            safe_json_content = re.sub(r'([a-zA-Z-]+)="([^"]*)"', r"\1='\2'", safe_json_content)

            # JSON 문자열 값들의 LaTeX 처리
            def process_json_string(match):
                field_value = match.group(1)
                # LaTeX 키워드 검사 (확장된 목록)
                latex_keywords = [
                    '\\\\', 'frac', 'sqrt', 'text', 'mathrm', 'times', 'cdot',
                    'pi', 'alpha', 'beta', 'gamma', 'theta', 'phi', 'lambda',
                    'delta', 'omega', 'sigma', 'left', 'right', 'overline', 'underline'
                ]

                if any(keyword in field_value for keyword in latex_keywords):
                    print(f"      [디버그] LaTeX 포함 필드 처리: {field_value[:50]}...")
                    # LaTeX가 포함된 문자열만 처리
                    fixed_value = fix_latex_backslashes(field_value)
                    return f'"{fixed_value}"'
                return match.group(0)

            # 모든 JSON 문자열 값을 LaTeX 패턴으로 처리
            latex_pattern = r'"([^"]*(?:\\\\|frac|sqrt|text|mathrm|times|cdot|pi|alpha|beta|gamma|theta|phi|lambda|delta|omega|sigma|left|right|overline|underline)[^"]*)"'
            latex_string_matches = re.findall(latex_pattern, safe_json_content)
            if latex_string_matches:
                print(f"      [디버그] LaTeX 포함 문자열 필드: {len(latex_string_matches)}개")

            safe_json_content = re.sub(latex_pattern, process_json_string, safe_json_content)

            print(f"      [디버그] 최종 안전 처리된 JSON 길이: {len(safe_json_content)} 문자")

            parsed_questions = json.loads(safe_json_content)

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

                # assessmentItemID 매칭
                question['id'] = find_matching_assessment_id(question, assessment_items)

                # 메타데이터 추가
                if i < len(assessment_items):
                    item = assessment_items[i]
                    # difficulty_band가 없거나 NULL인 경우 개념 기반 난이도 할당
                    db_difficulty = item.get('difficulty_band')
                    if not db_difficulty or db_difficulty == '중':
                        difficulty_band = get_concept_difficulty_band(item['concept_name'])
                    else:
                        difficulty_band = db_difficulty
                    
                    question['metadata'] = {
                        'grade': item['grade'],
                        'term': item['term'],
                        'concept_name': item['concept_name'],
                        'chapter_name': item.get('chapter_name', ''),
                        'difficulty_band': difficulty_band,
                        'knowledge_tag': item.get('knowledge_tag', ''),
                        'unit_name': item.get('unit_name', '')
                    }

                print(f"      [완료] 문제 {i+1}번: {question.get('concept_name', '?')} (ID: {question['id']})")
                print(f"         📝 문제: {question.get('question_text', 'N/A')}")
                print(f"         📋 선택지: {question.get('choices', 'N/A')}")
                print(f"         ✅ 정답: {question.get('correct_answer', 'N/A')}")
                print(f"         💡 해설: {question.get('answer_explanation', 'N/A')}")
                if question.get('svg_content'):
                    print(f"         🖼️  SVG: 있음 ({len(question['svg_content'])}자)")
                else:
                    print(f"         🖼️  SVG: 없음")
                if question.get('metadata'):
                    meta = question['metadata']
                    print(f"         📊 메타: grade={meta.get('grade','?')}, term={meta.get('term','?')}, concept={meta.get('concept_name','?')}")
                    print(f"               chapter={meta.get('chapter_name','?')}")
                    print(f"               difficulty={meta.get('difficulty_band','?')}, knowledge={meta.get('knowledge_tag','?')}")
                print()
                final_questions.append(question)

            print(f"      최종 {len(final_questions)}개 객관식 문제 검증 완료")
            logging.info(f"Successfully generated {len(final_questions)} questions")
            return final_questions

        except json.JSONDecodeError as e:
            print(f"      [오류] JSON 파싱 오류: {str(e)}")
            logging.error(f"JSON parsing error: {str(e)}")
            logging.error(f"Raw AI response: {ai_response}")

            # 파싱 오류 지점 상세 분석
            try:
                error_msg = str(e)
                if "char" in error_msg:
                    # char 위치 추출
                    char_pos = int(error_msg.split("char ")[1].split(")")[0])
                    print(f"      [분석] 오류 발생 위치: {char_pos}번째 문자")

                    # 오류 지점 주변 문자 출력 (앞뒤 50자씩)
                    start = max(0, char_pos - 50)
                    end = min(len(safe_json_content), char_pos + 50)
                    problem_section = safe_json_content[start:end]

                    print(f"      [분석] 문제 구간 ({start}~{end}): {repr(problem_section)}")
                    print(f"      [분석] 문제 문자: '{safe_json_content[char_pos] if char_pos < len(safe_json_content) else 'EOF'}'")

                    # 줄 단위로 분석
                    lines = safe_json_content[:char_pos].split('\n')
                    line_num = len(lines)
                    col_num = len(lines[-1]) if lines else 0
                    print(f"      [분석] 실제 위치: line {line_num}, column {col_num}")

            except Exception as analyze_error:
                print(f"      [분석 실패] {str(analyze_error)}")

            # 백업 파싱 시도 (강화된 버전)
            try:
                print("      [백업] 강화된 백업 파싱 시도 중...")
                backup_content = ai_response

                print(f"      [백업] 백업 처리 전 길이: {len(backup_content)} 문자")

                # 1. 모든 단일 백슬래시를 먼저 처리
                backup_content = re.sub(r'\\(?![\\"/bfnrt])', r'\\\\', backup_content)

                # 2. 특정 LaTeX 패턴들 강제 처리
                problematic_patterns = {
                    r'\\overline': r'\\\\overline',
                    r'\\overlin': r'\\\\overlin',  # 잘린 경우도 처리
                    r'\\underline': r'\\\\underline',
                    r'\\frac': r'\\\\frac',
                    r'\\sqrt': r'\\\\sqrt',
                    r'\\\(': r'\\\\(',  # \( 패턴
                    r'\\\)': r'\\\\)',  # \) 패턴
                }

                pattern_count = 0
                for old_pattern, new_pattern in problematic_patterns.items():
                    matches = re.findall(old_pattern, backup_content)
                    if matches:
                        pattern_count += len(matches)
                        print(f"      [백업] 문제 패턴 '{old_pattern}' 발견: {len(matches)}개")
                    backup_content = re.sub(old_pattern, new_pattern, backup_content)

                print(f"      [백업] 총 {pattern_count}개 문제 패턴 처리 완료")
                print(f"      [백업] 백업 처리 후 길이: {len(backup_content)} 문자")

                # 첫 번째 백업 파싱 시도
                try:
                    parsed_questions = json.loads(backup_content)
                    print(f"      [백업 성공] 1차 백업 파싱 성공")
                except json.JSONDecodeError as second_error:
                    print(f"      [백업 재시도] 1차 백업도 실패: {str(second_error)}")

                    # 최종 강제 처리: 모든 단일 백슬래시를 이중으로
                    print("      [최종시도] 모든 백슬래시 강제 이스케이프 적용")
                    final_backup = backup_content

                    # JSON 안전 문자를 제외한 모든 단일 백슬래시를 이중으로 변경
                    # 이미 이중인 것들은 보호하면서 처리
                    final_backup = re.sub(r'(?<!\\)\\(?![\\"/bfnrt])', r'\\\\', final_backup)

                    print(f"      [최종시도] 최종 처리 길이: {len(final_backup)} 문자")
                    parsed_questions = json.loads(final_backup)
                    print(f"      [최종 성공] 강제 이스케이프로 파싱 성공")
                print(f"      [성공] 백업 파싱으로 {len(parsed_questions)}개 문제 파싱됨")

                # 성공한 경우 동일한 검증 로직 적용
                final_questions = []
                for i, question in enumerate(parsed_questions):
                    if question.get('skip', False):
                        continue
                    if not question.get('choices') or len(question.get('choices', [])) != 4:
                        continue

                    question['id'] = find_matching_assessment_id(question, assessment_items)

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

                    final_questions.append(question)

                print(f"      [백업 성공] 최종 {len(final_questions)}개 문제 생성")
                return final_questions

            except Exception as backup_error:
                print(f"      [실패] 백업 파싱도 실패: {str(backup_error)}")
                logging.error(f"Backup parsing also failed: {str(backup_error)}")

                # 백업 파싱 실패 지점도 분석
                if isinstance(backup_error, json.JSONDecodeError):
                    try:
                        error_msg = str(backup_error)
                        if "char" in error_msg:
                            char_pos = int(error_msg.split("char ")[1].split(")")[0])
                            print(f"      [백업분석] 백업 오류 위치: {char_pos}번째 문자")

                            start = max(0, char_pos - 30)
                            end = min(len(backup_content), char_pos + 30)
                            problem_section = backup_content[start:end]

                            print(f"      [백업분석] 문제 구간: {repr(problem_section)}")
                            print(f"      [백업분석] 문제 문자: '{backup_content[char_pos] if char_pos < len(backup_content) else 'EOF'}'")
                    except:
                        pass

                return None

    except Exception as e:
        logging.error(f"Error generating RAG questions with AI: {str(e)}")
        return None