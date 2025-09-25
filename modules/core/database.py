import pyodbc
import logging
import os

# 전역 캐시 변수
CONCEPT_NAMES_CACHE = []
CONCEPT_MAPPING_CACHE = {}


def get_sql_connection():
    """SQL Server 연결 초기화"""
    try:
        conn = pyodbc.connect(os.environ["SQL_CONNECTION"])
        # 강화된 한글/유니코드 처리 설정
        conn.setdecoding(pyodbc.SQL_CHAR, encoding='utf-8')
        conn.setdecoding(pyodbc.SQL_WCHAR, encoding='utf-8')
        conn.setdecoding(pyodbc.SQL_WMETADATA, encoding='utf-8')
        conn.setencoding(encoding='utf-8')
        # autocommit 설정으로 트랜잭션 문제 방지
        conn.autocommit = True
        return conn
    except Exception as e:
        logging.error(f"SQL connection error: {str(e)}")
        return None


def get_question_data(mode, topic_name=None):
    """SQL에서 문제 관련 데이터 가져오기 - 통합 함수

    mode:
    - "params": 문제 파라미터들 (grade, term, topic_name, question_type, difficulty)
    - "questions": 기존 문제 내용들 (AI 프롬프트용)
    - "topic_code": 주제 코드
    """
    try:
        conn = get_sql_connection()
        if not conn:
            if mode == "params":
                return None
            elif mode == "questions":
                return "기존 문제를 가져올 수 없습니다."
            elif mode == "topic_code":
                return "9000000"

        cursor = conn.cursor()

        if mode == "params":
            # 첫 번째 레코드에서 파라미터들 가져오기 (ID 포함)
            cursor.execute("""
                SELECT TOP 1 id, question_grade, question_term, question_topic_name, question_type1, question_difficulty
                FROM questions_dim
            """)
            result = cursor.fetchone()
            conn.close()

            if result:
                return {
                    'id': result[0],
                    'grade': result[1],
                    'term': result[2],
                    'topic_name': result[3],
                    'question_type': result[4],
                    'difficulty': result[5]
                }
            return None

        elif mode == "questions":
            # 해당 주제의 기존 문제들 가져오기
            cursor.execute("""
                SELECT TOP 2 question_text, question_type1
                FROM questions_dim
                WHERE question_topic_name LIKE ?
            """, f'%{topic_name}%')

            results = cursor.fetchall()
            conn.close()

            if results:
                question_text = "기존 문제 예시:\n"
                for i, (content, qtype) in enumerate(results, 1):
                    question_text += f"{i}. [{qtype}] {content[:100]}...\n"
                return question_text
            else:
                return "기존 문제 예시를 찾을 수 없습니다."

        elif mode == "topic_code":
            # 주제 코드 가져오기
            cursor.execute("""
                SELECT TOP 1 question_topic
                FROM questions_dim
                WHERE question_topic_name LIKE ?
            """, f'%{topic_name}%')

            result = cursor.fetchone()
            conn.close()

            if result and result[0]:
                return result[0]
            else:
                return "9000000"

    except Exception as e:
        logging.error(f"Error getting question data (mode: {mode}): {str(e)}")
        if mode == "params":
            return None
        elif mode == "questions":
            return "데이터를 가져오는 중 오류가 발생했습니다."
        elif mode == "topic_code":
            return "9000000"


def save_to_database(question_record, answer_record):
    """DB에 문제와 정답 저장"""
    try:
        conn = get_sql_connection()
        if not conn:
            return False

        cursor = conn.cursor()

        # questions_dim에 삽입
        question_sql = """
            INSERT INTO questions_dim (
                id, question_grade, question_term, question_unit, question_topic,
                question_topic_name, question_type1, question_type2, question_sector1,
                question_sector2, question_step, question_difficulty, question_text,
                question_filename, similar_question, question_condition
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        cursor.execute(question_sql, (
            question_record['id'], question_record['question_grade'],
            question_record['question_term'], question_record['question_unit'],
            question_record['question_topic'], question_record['question_topic_name'],
            question_record['question_type1'], question_record['question_type2'],
            question_record['question_sector1'], question_record['question_sector2'],
            question_record['question_step'], question_record['question_difficulty'],
            question_record['question_text'], question_record['question_filename'],
            question_record['similar_question'], question_record['question_condition']
        ))

        # answers_dim에 삽입
        answer_sql = """
            INSERT INTO answers_dim (id, answer_filename, answer_text, answer_by_ai)
            VALUES (?, ?, ?, ?)
        """

        cursor.execute(answer_sql, (
            answer_record['id'], answer_record['answer_filename'],
            answer_record['answer_text'], answer_record['answer_by_ai']
        ))

        conn.commit()
        conn.close()

        logging.info(f"Successfully saved question {question_record['id']} to database")
        return True

    except Exception as e:
        logging.error(f"Database save error: {str(e)}")
        if conn:
            conn.rollback()
            conn.close()
        return False


def load_concept_names():
    """gold_knowledgeTag 테이블에서 concept_name 목록 로드"""
    global CONCEPT_NAMES_CACHE, CONCEPT_MAPPING_CACHE

    try:
        conn = get_sql_connection()
        if not conn:
            logging.error("Failed to connect to database for concept names")
            return False

        cursor = conn.cursor()
        cursor.execute("""
            SELECT DISTINCT knowledgeTag, concept_name
            FROM gold.gold_knowledgeTag
            WHERE concept_name IS NOT NULL
            ORDER BY concept_name
        """)

        results = cursor.fetchall()
        conn.close()

        if results:
            CONCEPT_NAMES_CACHE = [row[1] for row in results]  # concept_name만
            CONCEPT_MAPPING_CACHE = {row[1]: row[0] for row in results}  # concept_name -> knowledgeTag

            logging.info(f"Loaded {len(CONCEPT_NAMES_CACHE)} concept names into cache")
            return True
        else:
            logging.warning("No concept names found in gold_knowledgeTag table")
            return False

    except Exception as e:
        logging.error(f"Error loading concept names: {str(e)}")
        return False


def get_cached_concept_names():
    """캐시된 concept_name 목록 반환"""
    global CONCEPT_NAMES_CACHE

    if not CONCEPT_NAMES_CACHE:
        load_concept_names()

    return CONCEPT_NAMES_CACHE


def get_knowledge_tag_by_concept(concept_name):
    """concept_name으로 knowledgeTag 조회"""
    global CONCEPT_MAPPING_CACHE

    if not CONCEPT_MAPPING_CACHE:
        load_concept_names()

    return CONCEPT_MAPPING_CACHE.get(concept_name, None)


def get_mapped_concept_name(topic_name):
    """questions_dim에서 topic_name에 매핑된 concept_by_ai 조회"""
    try:
        conn = get_sql_connection()
        if not conn:
            return None

        cursor = conn.cursor()
        cursor.execute("""
            SELECT TOP 1 concept_by_ai
            FROM questions_dim
            WHERE question_topic_name = ? AND concept_by_ai IS NOT NULL
        """, topic_name)

        result = cursor.fetchone()
        conn.close()

        return result[0] if result else None

    except Exception as e:
        logging.error(f"Error getting mapped concept name: {str(e)}")
        return None