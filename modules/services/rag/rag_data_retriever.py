# -*- coding: utf-8 -*-
"""
RAG 데이터 조회 모듈
데이터베이스에서 개념별 정답률과 assessmentItemID를 조회하는 기능 전담
디버깅: DB 연결, 쿼리 결과, 데이터 품질 등을 집중적으로 확인 가능
"""
import logging
from collections import defaultdict
import math
from ...core.database import get_sql_connection


class RAGDataRetriever:
    """RAG에서 사용할 데이터를 데이터베이스에서 조회하는 클래스"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def get_top_concepts_by_accuracy(self, grade, top_k=3):
        """
        정답률 기반으로 Top-K 개념 선택 (chapter_name 첫 번째 부분 기준)

        Args:
            grade (int): 국제식 학년 (7, 8, 9)
            top_k (int): 선택할 개념 수

        Returns:
            list: 개념 정보 리스트 또는 None
        """
        try:
            print(f"      [데이터조회] 데이터베이스 연결 중...")
            conn = get_sql_connection()
            if not conn:
                print(f"      [데이터조회] 데이터베이스 연결 실패!")
                return None

            cursor = conn.cursor()
            print(f"      [데이터조회] grade={grade}에 대한 쿼리 실행 중...")

            # 1단계: 전체 레코드 수 확인
            cursor.execute("SELECT COUNT(*) FROM gold.vw_personal_item_enriched")
            total_count = cursor.fetchone()[0]
            print(f"      [데이터조회] 전체 레코드 수: {total_count}")

            # 2단계: 해당 grade 데이터 확인
            cursor.execute(f"SELECT COUNT(*) FROM gold.vw_personal_item_enriched WHERE grade = {grade}")
            grade_count = cursor.fetchone()[0]
            print(f"      [데이터조회] Grade {grade} 레코드 수: {grade_count}")

            # 3단계: 샘플 데이터 확인
            if grade_count > 0:
                try:
                    def safe_decode(value):
                        """초강력 한글 디코딩"""
                        if value is None:
                            return "None"

                        # 이미 문자열이면 그대로 반환
                        if isinstance(value, str):
                            return value

                        # bytes인 경우 여러 인코딩 시도
                        if isinstance(value, bytes):
                            encodings = ['utf-8', 'cp949', 'euc-kr', 'utf-16', 'ascii']
                            for encoding in encodings:
                                try:
                                    return value.decode(encoding)
                                except (UnicodeDecodeError, UnicodeError):
                                    continue
                            # 모든 인코딩 실패시 에러 무시하고 변환
                            return value.decode('utf-8', errors='replace')

                        # 기타 타입은 문자열로 변환
                        try:
                            return str(value)
                        except:
                            return "변환실패"

                    cursor.execute(f"SELECT TOP 3 ISNULL(TRY_CAST(concept_name AS NVARCHAR(MAX)), 'Unknown') as concept_name, is_correct FROM gold.vw_personal_item_enriched WHERE grade = {grade}")
                    sample_data = cursor.fetchall()
                    print(f"      [데이터조회] 샘플 데이터:")
                    for i, (concept, is_correct) in enumerate(sample_data):
                        try:
                            safe_concept = safe_decode(concept)
                            print(f"         {i+1}. {safe_concept} | is_correct: {is_correct}")
                        except Exception as decode_error:
                            print(f"         {i+1}. [디코딩 실패: {str(decode_error)}] | is_correct: {is_correct}")
                            safe_concept = "디코딩_실패"
                except Exception as e:
                    print(f"      [데이터조회] 샘플 데이터 쿼리 실패: {str(e)}")

            # 4단계: 메인 쿼리 실행
            try:
                query = f"""
                    WITH primary_chapters AS (
                        SELECT
                            CASE
                                WHEN CHARINDEX('>', ISNULL(TRY_CAST(chapter_name AS NVARCHAR(MAX)), 'Unknown')) > 0
                                THEN LTRIM(RTRIM(SUBSTRING(ISNULL(TRY_CAST(chapter_name AS NVARCHAR(MAX)), 'Unknown'), 1, CHARINDEX('>', ISNULL(TRY_CAST(chapter_name AS NVARCHAR(MAX)), 'Unknown')) - 1)))
                                ELSE ISNULL(TRY_CAST(chapter_name AS NVARCHAR(MAX)), 'Unknown')
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
                print(f"      [데이터조회] 메인 쿼리 실행 중...")

                cursor.execute(query)
                results = cursor.fetchall()
                print(f"      [데이터조회] 쿼리 결과: {len(results)}개 개념")

                if results:
                    print(f"      [데이터조회] 상위 3개 결과:")
                    for i, result in enumerate(results[:3]):
                        print(f"         {i+1}. {result[0]} (정답률: {result[1]:.3f}, 문항수: {result[2]})")

                conn.close()

                if results:
                    def safe_decode(value):
                        """초강력 한글 디코딩"""
                        if value is None:
                            return "None"

                        # 이미 문자열이면 그대로 반환
                        if isinstance(value, str):
                            return value

                        # bytes인 경우 여러 인코딩 시도
                        if isinstance(value, bytes):
                            encodings = ['utf-8', 'cp949', 'euc-kr', 'utf-16', 'ascii']
                            for encoding in encodings:
                                try:
                                    return value.decode(encoding)
                                except (UnicodeDecodeError, UnicodeError):
                                    continue
                            # 모든 인코딩 실패시 에러 무시하고 변환
                            return value.decode('utf-8', errors='replace')

                        # 기타 타입은 문자열로 변환
                        try:
                            return str(value)
                        except:
                            return "변환실패"

                    concepts = []
                    for result in results:
                        try:
                            safe_chapter = safe_decode(result[0])
                            if safe_chapter and safe_chapter.strip() and safe_chapter != 'Unknown':
                                concepts.append({
                                    'primary_chapter': safe_chapter,
                                    'avg_correct_rate': result[1],
                                    'item_count': result[2]
                                })
                                print(f"         ✓ 추가된 개념: {safe_chapter} (정답률: {result[1]:.3f})")
                            else:
                                print(f"         ✗ 스킵된 개념: {safe_chapter} (빈 값 또는 Unknown)")
                        except Exception as decode_error:
                            print(f"         ✗ 디코딩 실패 스킵: {str(decode_error)}")
                            continue

                    selected_concepts = concepts[:top_k] if len(concepts) >= top_k else concepts
                    print(f"      [데이터조회] 최종 선택된 개념: {len(selected_concepts)}개")
                    return selected_concepts

                return []

            except Exception as e:
                print(f"      [데이터조회] 메인 쿼리 실패: {str(e)}")
                conn.close()
                return []

        except Exception as e:
            self.logger.error(f"Error getting top concepts by accuracy: {str(e)}")
            print(f"      [데이터조회] 전체 프로세스 오류: {str(e)}")
            return None

    def get_assessment_ids_by_concepts(self, concepts, target_count=6):
        """
        개념별 assessmentItemID 수집 및 6개 확정

        Args:
            concepts (list): 선택된 개념 리스트
            target_count (int): 목표 ID 수

        Returns:
            list: assessmentItemID 정보 리스트 또는 None
        """
        try:
            print(f"      [ID수집] {len(concepts)}개 개념에서 {target_count}개 ID 수집 시작")
            conn = get_sql_connection()
            if not conn:
                print(f"      [ID수집] 데이터베이스 연결 실패")
                return None

            cursor = conn.cursor()
            all_ids = []

            # 각 primary chapter별 ID 수집
            for i, concept in enumerate(concepts):
                primary_chapter = concept['primary_chapter']
                print(f"      [ID수집] {i+1}/{len(concepts)}: '{primary_chapter}' 개념 처리 중")

                # chapter_name이 해당 primary chapter로 시작하는 레코드들 조회
                cursor.execute("""
                    SELECT DISTINCT
                        assessmentItemID,
                        concept_name,
                        grade,
                        term,
                        chapter_name,
                        difficulty_band
                    FROM gold.vw_personal_item_enriched
                    WHERE grade = 8
                      AND (
                          CAST(chapter_name AS NVARCHAR(MAX)) LIKE ? + ' > %'
                          OR CAST(chapter_name AS NVARCHAR(MAX)) = ?
                      )
                    ORDER BY assessmentItemID
                """, (primary_chapter, primary_chapter))

                results = cursor.fetchall()
                print(f"         └─ {len(results)}개 ID 발견")

                for result in results:
                    all_ids.append({
                        'assessment_item_id': result[0],
                        'concept_name': result[1],
                        'grade': result[2],
                        'term': result[3],
                        'chapter_name': result[4],
                        'difficulty_band': result[5] if len(result) > 5 else None
                    })

            conn.close()
            print(f"      [ID수집] 전체 수집된 ID: {len(all_ids)}개")

            # ID 개수 조정
            if len(all_ids) == target_count:
                print(f"      [ID수집] 정확히 {target_count}개 - 조정 불필요")
                return all_ids
            elif len(all_ids) < target_count:
                print(f"      [ID수집] 부족함 ({len(all_ids)}/{target_count}) - 추가 ID 검색")
                return self._get_additional_ids(all_ids, target_count - len(all_ids))
            else:
                print(f"      [ID수집] 초과함 ({len(all_ids)}/{target_count}) - 균등 샘플링 적용")
                return self._balance_ids_by_concept(all_ids, target_count)

        except Exception as e:
            self.logger.error(f"Error getting assessment IDs by concepts: {str(e)}")
            print(f"      [ID수집] 오류 발생: {str(e)}")
            return None

    def _get_additional_ids(self, existing_ids, needed_count):
        """부족분을 하위 개념에서 보충"""
        try:
            print(f"      [추가ID] {needed_count}개 추가 ID 검색 중")
            conn = get_sql_connection()
            if not conn:
                return existing_ids

            cursor = conn.cursor()

            # 이미 사용된 개념 제외
            used_concepts = set(item['concept_name'] for item in existing_ids)
            concept_filter = "'" + "','".join(used_concepts) + "'" if used_concepts else "''"

            cursor.execute(f"""
                SELECT TOP {needed_count}
                    assessmentItemID,
                    concept_name,
                    grade,
                    term,
                    chapter_name,
                    difficulty_band
                FROM gold.vw_personal_item_enriched
                WHERE grade = 8
                AND concept_name NOT IN ({concept_filter})
                ORDER BY assessmentItemID
            """)

            results = cursor.fetchall()
            conn.close()

            print(f"      [추가ID] {len(results)}개 추가 ID 발견")
            for result in results:
                existing_ids.append({
                    'assessment_item_id': result[0],
                    'concept_name': result[1],
                    'grade': result[2],
                    'term': result[3],
                    'chapter_name': result[4],
                    'difficulty_band': result[5] if len(result) > 5 else None
                })

            print(f"      [추가ID] 최종 ID 수: {len(existing_ids)}개")
            return existing_ids

        except Exception as e:
            self.logger.error(f"Error getting additional IDs: {str(e)}")
            print(f"      [추가ID] 오류 발생: {str(e)}")
            return existing_ids

    def _balance_ids_by_concept(self, all_ids, target_count):
        """개념별 균등 샘플링으로 6개 맞춤"""
        print(f"      [균등샘플링] {len(all_ids)}개에서 {target_count}개로 균등 샘플링")

        # 개념별 그룹화
        concept_groups = defaultdict(list)
        for item in all_ids:
            concept_groups[item['concept_name']].append(item)

        balanced_ids = []
        concepts = list(concept_groups.keys())
        items_per_concept = target_count // len(concepts)
        remaining = target_count % len(concepts)

        print(f"      [균등샘플링] {len(concepts)}개 개념, 개념당 {items_per_concept}개씩 (+{remaining}개 추가)")

        for i, concept in enumerate(concepts):
            concept_items = concept_groups[concept]

            # 각 개념별 할당량 계산
            take_count = items_per_concept
            if i < remaining:  # 나머지를 앞쪽 개념들에 분배
                take_count += 1

            selected_items = concept_items[:take_count]
            balanced_ids.extend(selected_items)

            print(f"         {i+1}. {concept}: {len(selected_items)}개 선택")

            if len(balanced_ids) >= target_count:
                break

        final_result = balanced_ids[:target_count]
        print(f"      [균등샘플링] 최종 선택: {len(final_result)}개")
        return final_result