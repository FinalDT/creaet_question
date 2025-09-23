# -*- coding: utf-8 -*-
"""
DB 업데이트 관련 함수들
"""
import logging
from modules.database import get_sql_connection


def update_concept_by_ai_batch(topic_concept_pairs):
    """배치로 concept_by_ai 업데이트 (50개씩)"""
    try:
        conn = get_sql_connection()
        if not conn:
            logging.error("DB 연결 실패")
            return 0

        cursor = conn.cursor()

        # CASE WHEN 구문 생성
        case_statements = []
        topic_list = []

        for topic_name, concept_name in topic_concept_pairs:
            escaped_topic = topic_name.replace("'", "''")
            escaped_concept = concept_name.replace("'", "''")

            case_statements.append(f"WHEN N'{escaped_topic}' THEN N'{escaped_concept}'")
            topic_list.append(f"N'{escaped_topic}'")

        update_query = f"""
            UPDATE questions_dim
            SET concept_by_ai = CASE question_topic_name COLLATE Korean_Wansung_CI_AS
                {chr(10).join(case_statements)}
            END
            WHERE question_topic_name COLLATE Korean_Wansung_CI_AS IN ({', '.join(topic_list)})
        """

        cursor.execute(update_query)
        affected_rows = cursor.rowcount

        conn.commit()
        conn.close()

        return affected_rows

    except Exception as e:
        logging.error(f"배치 DB 업데이트 실패: {str(e)}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return 0


def update_concept_by_ai(topic_name, concept_name):
    """단일 concept_by_ai 업데이트 (하위 호환성)"""
    return update_concept_by_ai_batch([(topic_name, concept_name)]) > 0


def get_concepts_for_knowledge_mapping():
    """concept_by_ai가 설정된 행들의 concept 목록 조회"""
    try:
        conn = get_sql_connection()
        if not conn:
            return []

        cursor = conn.cursor()
        cursor.execute("""
            SELECT DISTINCT concept_by_ai, COUNT(*) as row_count
            FROM questions_dim
            WHERE concept_by_ai IS NOT NULL
            GROUP BY concept_by_ai
            ORDER BY concept_by_ai
        """)

        results = cursor.fetchall()
        conn.close()

        return [(row[0], row[1]) for row in results]

    except Exception as e:
        logging.error(f"concept 목록 조회 실패: {str(e)}")
        return []


def get_knowledge_tag_for_concept(concept_name):
    """concept_name으로 knowledgeTag 조회"""
    try:
        conn = get_sql_connection()
        if not conn:
            return None

        cursor = conn.cursor()
        escaped_concept = concept_name.replace("'", "''")

        cursor.execute(f"""
            SELECT TOP 1 knowledgeTag
            FROM gold.gold_knowledgeTag
            WHERE concept_name = N'{escaped_concept}' COLLATE Korean_Wansung_CI_AS
        """)

        result = cursor.fetchone()
        conn.close()

        return result[0] if result else None

    except Exception as e:
        logging.error(f"knowledgeTag 조회 실패: {str(e)}")
        return None


def update_knowledge_tag(concept_name, knowledge_tag):
    """concept_by_ai로 knowledgeTag 업데이트"""
    try:
        conn = get_sql_connection()
        if not conn:
            return False

        cursor = conn.cursor()

        escaped_concept = concept_name.replace("'", "''")
        # knowledgeTag는 int이므로 직접 사용

        update_query = f"""
            UPDATE questions_dim
            SET knowledgeTag = {knowledge_tag}
            WHERE concept_by_ai = N'{escaped_concept}' COLLATE Korean_Wansung_CI_AS
        """

        cursor.execute(update_query)
        affected_rows = cursor.rowcount

        conn.commit()
        conn.close()

        return affected_rows > 0

    except Exception as e:
        logging.error(f"knowledgeTag 업데이트 실패: {str(e)}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return False


def get_questions_with_knowledge_tag():
    """knowledgeTag가 있는 모든 문제 조회"""
    try:
        conn = get_sql_connection()
        if not conn:
            return []

        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, question_topic_name, knowledgeTag
            FROM questions_dim
            WHERE knowledgeTag IS NOT NULL
            ORDER BY id
        """)

        results = cursor.fetchall()
        conn.close()

        return [(row[0], row[1], row[2]) for row in results]

    except Exception as e:
        logging.error(f"knowledgeTag 문제 조회 실패: {str(e)}")
        return []


def load_all_assessment_mappings():
    """모든 knowledgeTag → assessmentItemID 매핑을 한 번에 로드"""
    try:
        conn = get_sql_connection()
        if not conn:
            return {}

        cursor = conn.cursor()
        cursor.execute("""
            SELECT knowledgeTag, assessmentItemID
            FROM gold.gold_knowledgeTag_dim
            WHERE knowledgeTag IS NOT NULL AND assessmentItemID IS NOT NULL
            ORDER BY knowledgeTag, assessmentItemID
        """)

        results = cursor.fetchall()
        conn.close()

        # knowledgeTag별로 assessmentItemID 리스트 생성
        mappings = {}
        for knowledge_tag, assessment_id in results:
            if knowledge_tag not in mappings:
                mappings[knowledge_tag] = []
            mappings[knowledge_tag].append(assessment_id)

        # 디버깅: 특정 knowledgeTag 확인
        test_tags = [4959, 1180, 1181]
        for tag in test_tags:
            if tag in mappings:
                print(f"🔍 디버깅: knowledgeTag {tag} → {len(mappings[tag])}개 assessmentItemID 로드됨")
                print(f"    첫 5개: {mappings[tag][:5]}")
            else:
                print(f"❌ 디버깅: knowledgeTag {tag} 매핑에서 누락됨")

        logging.info(f"전체 매핑 로드 완료: {len(mappings)}개 knowledgeTag, {len(results)}개 assessmentItemID")
        return mappings

    except Exception as e:
        logging.error(f"전체 매핑 로드 실패: {str(e)}")
        return {}


def get_assessment_items_for_knowledge_tag(knowledge_tag):
    """특정 knowledgeTag에 해당하는 모든 assessmentItemID 조회 (하위 호환성)"""
    try:
        conn = get_sql_connection()
        if not conn:
            return []

        cursor = conn.cursor()
        cursor.execute(f"""
            SELECT DISTINCT assessmentItemID
            FROM gold.gold_knowledgeTag_dim
            WHERE knowledgeTag = {knowledge_tag}
            ORDER BY assessmentItemID
        """)

        results = cursor.fetchall()
        conn.close()

        return [row[0] for row in results if row[0]]

    except Exception as e:
        logging.error(f"assessmentItemID 조회 실패 (knowledgeTag: {knowledge_tag}): {str(e)}")
        return []


def assign_assessment_item_id_fast(knowledge_tag, used_items_by_tag, all_mappings):
    """최적화된 assessmentItemID 할당 (사전 로드된 매핑 사용)"""
    # 타입 변환: 문자열을 정수로 변환
    try:
        if isinstance(knowledge_tag, str):
            knowledge_tag_int = int(knowledge_tag)
        else:
            knowledge_tag_int = knowledge_tag
    except (ValueError, TypeError):
        return None, f"knowledgeTag {knowledge_tag} 타입 변환 실패"

    # 사전 로드된 매핑에서 가져오기 (정수 키 사용)
    available_items = all_mappings.get(knowledge_tag_int, [])

    if not available_items:
        return None, f"knowledgeTag {knowledge_tag}에 대한 assessmentItemID 없음"

    # 이미 사용된 항목들 확인 (원본 키 사용)
    used_items = used_items_by_tag.get(knowledge_tag, set())

    # 사용되지 않은 첫 번째 항목 선택
    for item_id in available_items:
        if item_id not in used_items:
            # 사용 목록에 추가 (원본 키 사용)
            if knowledge_tag not in used_items_by_tag:
                used_items_by_tag[knowledge_tag] = set()
            used_items_by_tag[knowledge_tag].add(item_id)

            return item_id, "성공"

    # 모든 항목이 사용된 경우
    return None, f"knowledgeTag {knowledge_tag}의 모든 assessmentItemID 사용됨 ({len(available_items)}개)"


def assign_assessment_item_id(knowledge_tag, used_items_by_tag):
    """knowledgeTag별 사용되지 않은 assessmentItemID 선택 (하위 호환성)"""
    # 해당 knowledgeTag의 모든 assessmentItemID 가져오기
    available_items = get_assessment_items_for_knowledge_tag(knowledge_tag)

    if not available_items:
        return None, f"knowledgeTag {knowledge_tag}에 대한 assessmentItemID 없음"

    # 이미 사용된 항목들 확인
    used_items = used_items_by_tag.get(knowledge_tag, set())

    # 사용되지 않은 첫 번째 항목 선택
    for item_id in available_items:
        if item_id not in used_items:
            # 사용 목록에 추가
            if knowledge_tag not in used_items_by_tag:
                used_items_by_tag[knowledge_tag] = set()
            used_items_by_tag[knowledge_tag].add(item_id)

            return item_id, "성공"

    # 모든 항목이 사용된 경우
    return None, f"knowledgeTag {knowledge_tag}의 모든 assessmentItemID 사용됨 ({len(available_items)}개)"


def check_concept_completion():
    """concept_by_ai 매핑 완료 상태 체크"""
    try:
        conn = get_sql_connection()
        if not conn:
            return False, 0, 0

        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                COUNT(*) as total_rows,
                SUM(CASE WHEN concept_by_ai IS NOT NULL THEN 1 ELSE 0 END) as completed_rows
            FROM questions_dim
        """)

        result = cursor.fetchone()
        conn.close()

        if result:
            total, completed = result
            completion_rate = (completed / total) * 100 if total > 0 else 0
            # 95% 이상 완료되었으면 완료로 간주 (일부 실패 허용)
            is_completed = completion_rate >= 95
            return is_completed, completed, total

        return False, 0, 0

    except Exception as e:
        logging.error(f"concept 완료 상태 체크 실패: {str(e)}")
        return False, 0, 0


def check_knowledge_tag_completion():
    """knowledgeTag 매핑 완료 상태 체크"""
    try:
        conn = get_sql_connection()
        if not conn:
            return False, 0, 0

        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                COUNT(*) as total_rows,
                SUM(CASE WHEN knowledgeTag IS NOT NULL THEN 1 ELSE 0 END) as completed_rows
            FROM questions_dim
            WHERE concept_by_ai IS NOT NULL
        """)

        result = cursor.fetchone()
        conn.close()

        if result:
            total, completed = result
            completion_rate = (completed / total) * 100 if total > 0 else 0
            # 95% 이상 완료되었으면 완료로 간주
            is_completed = completion_rate >= 95
            return is_completed, completed, total

        return False, 0, 0

    except Exception as e:
        logging.error(f"knowledgeTag 완료 상태 체크 실패: {str(e)}")
        return False, 0, 0


def update_knowledge_tag_batch(concept_tag_pairs):
    """배치로 knowledgeTag 업데이트"""
    try:
        conn = get_sql_connection()
        if not conn:
            logging.error("DB 연결 실패")
            return 0

        cursor = conn.cursor()

        # CASE WHEN 구문 생성
        case_statements = []
        concept_list = []

        for concept_name, knowledge_tag in concept_tag_pairs:
            escaped_concept = concept_name.replace("'", "''")
            case_statements.append(f"WHEN N'{escaped_concept}' THEN {knowledge_tag}")
            concept_list.append(f"N'{escaped_concept}'")

        update_query = f"""
            UPDATE questions_dim
            SET knowledgeTag = CASE concept_by_ai COLLATE Korean_Wansung_CI_AS
                {chr(10).join(case_statements)}
            END
            WHERE concept_by_ai COLLATE Korean_Wansung_CI_AS IN ({', '.join(concept_list)})
        """

        cursor.execute(update_query)
        affected_rows = cursor.rowcount

        conn.commit()
        conn.close()

        return affected_rows

    except Exception as e:
        logging.error(f"배치 knowledgeTag 업데이트 실패: {str(e)}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return 0


def verify_update(topic_name):
    """업데이트 결과 확인 (디버깅용)"""
    try:
        conn = get_sql_connection()
        if not conn:
            return None

        cursor = conn.cursor()
        escaped_topic = topic_name.replace("'", "''")

        cursor.execute(f"""
            SELECT concept_by_ai, COUNT(*) as cnt
            FROM questions_dim
            WHERE question_topic_name = N'{escaped_topic}' COLLATE Korean_Wansung_CI_AS
            GROUP BY concept_by_ai
        """)

        results = cursor.fetchall()
        conn.close()

        return results

    except Exception as e:
        logging.error(f"업데이트 확인 실패: {str(e)}")
        return None