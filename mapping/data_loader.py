# -*- coding: utf-8 -*-
"""
데이터 로딩 관련 함수들
"""
import logging
from modules.database import get_sql_connection


def get_unique_topic_names():
    """DB에서 고유한 topic_name과 샘플 question_text 가져오기"""
    try:
        conn = get_sql_connection()
        if not conn:
            logging.error("DB 연결 실패")
            return []

        cursor = conn.cursor()
        cursor.execute("""
            SELECT DISTINCT t1.question_topic_name, t2.question_text
            FROM (
                SELECT question_topic_name, MIN(id) as min_id
                FROM questions_dim
                WHERE question_topic_name IS NOT NULL
                GROUP BY question_topic_name
            ) t1
            INNER JOIN questions_dim t2 ON t1.min_id = t2.id
            ORDER BY t1.question_topic_name
        """)

        results = cursor.fetchall()
        conn.close()

        topic_data = [(row[0], row[1]) for row in results if row[0]]
        logging.info(f"✅ questions_dim에서 {len(topic_data)}개 주제 발견")
        return topic_data

    except Exception as e:
        logging.error(f"topic_name 로딩 실패: {str(e)}")
        return []


def count_topic_rows(topic_name):
    """특정 topic_name의 행 수 조회 (디버깅용)"""
    try:
        conn = get_sql_connection()
        if not conn:
            return 0

        cursor = conn.cursor()

        # 파라미터 바인딩 방식
        cursor.execute("SELECT COUNT(*) FROM questions_dim WHERE question_topic_name = ?", topic_name)
        count1 = cursor.fetchone()[0]

        # 직접 문자열 방식
        escaped_topic = topic_name.replace("'", "''")
        cursor.execute(f"SELECT COUNT(*) FROM questions_dim WHERE question_topic_name = N'{escaped_topic}' COLLATE Korean_Wansung_CI_AS")
        count2 = cursor.fetchone()[0]

        conn.close()

        print(f"      🔧 실행할 쿼리 확인...")
        print(f"      📊 방법1 (파라미터 바인딩): {count1}개")
        print(f"      📊 방법2 (직접 문자열): {count2}개")
        print(f"      📊 최종 결과: {count2}개")

        return count2

    except Exception as e:
        logging.error(f"행 수 조회 실패: {str(e)}")
        return 0


def debug_topic_info(topic_name):
    """디버깅용 topic 정보 출력 (간소화)"""
    # 디버깅 정보는 배치 처리에서 불필요하므로 생략
    return 0