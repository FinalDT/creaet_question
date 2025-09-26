# -*- coding: utf-8 -*-
"""
RAG 유틸리티 모듈
공통으로 사용되는 헬퍼 함수들을 모아놓은 모듈
디버깅: 각 함수별 입출력을 독립적으로 테스트 가능
"""
import logging
from ...core.utils import generate_question_id


class RAGUtils:
    """RAG에서 사용하는 유틸리티 함수들을 모아놓은 클래스"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    @staticmethod
    def extract_primary_chapter(chapter_name):
        """
        chapter_name에서 첫 번째 주제 추출

        Args:
            chapter_name (str): 원본 장 이름

        Returns:
            str: 첫 번째 주제명

        Examples:
            '이차방정식 > 이차방정식 > 제곱근을 이용한 이차방정식의 풀이' → '이차방정식'
        """
        if not chapter_name:
            return chapter_name

        # '>' 구분자로 분리하여 첫 번째 부분 추출
        parts = chapter_name.split('>')
        result = parts[0].strip() if parts else chapter_name

        print(f"      [유틸] 장 이름 추출: '{chapter_name}' → '{result}'")
        return result

    @staticmethod
    def get_concept_difficulty_band(concept_name):
        """
        개념명 기반 난이도 판단 (임시 해결책)

        Args:
            concept_name (str): 개념명

        Returns:
            str: 난이도 ('상', '중', '하')
        """
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
                print(f"      [유틸] 난이도 판단: '{concept_name}' → 상 (키워드: {keyword})")
                return "상"

        # 저난이도 체크
        for keyword in low_difficulty_keywords:
            if keyword in concept_lower:
                print(f"      [유틸] 난이도 판단: '{concept_name}' → 하 (키워드: {keyword})")
                return "하"

        # 기본값 (중간 난이도)
        print(f"      [유틸] 난이도 판단: '{concept_name}' → 중 (기본값)")
        return "중"

    @staticmethod
    def find_matching_assessment_id(question, assessment_items):
        """
        생성된 문제의 주제에 맞는 assessmentItemID 찾기

        Args:
            question (dict): 생성된 문제 정보
            assessment_items (list): 사용 가능한 assessment item 리스트

        Returns:
            str: 매칭된 assessmentItemID
        """
        question_text = question.get('question_text', '').lower()
        print(f"      [유틸] ID 매칭 시작: '{question_text[:50]}...'")

        # 키워드 기반 매칭 룰
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
            print(f"      [유틸] 매칭 시도: '{concept_name}'")

            # concept_name과 직접 비교
            concept_keywords_to_check = concept_keywords.get(concept_name.split()[0], [])
            matched_keywords = [kw for kw in concept_keywords_to_check if kw in question_text]

            if matched_keywords:
                matched_id = item['assessment_item_id']
                print(f"      [유틸] 매칭 성공: '{concept_name}' → {matched_id} (키워드: {matched_keywords})")
                return matched_id

        # 매칭 실패 시 첫번째 항목 반환 (fallback)
        fallback_id = assessment_items[0]['assessment_item_id'] if assessment_items else generate_question_id()
        print(f"      [유틸] 매칭 실패 - 첫 번째 ID 사용: {fallback_id}")
        return fallback_id

    @staticmethod
    def create_rag_context_block(assessment_items):
        """
        RAG 컨텍스트 블록 생성

        Args:
            assessment_items (list): assessment item 리스트

        Returns:
            str: RAG용 컨텍스트 블록 문자열
        """
        print(f"      [유틸] 컨텍스트 블록 생성: {len(assessment_items)}개 항목")

        context_lines = ["불변 목록 (각 행당 정확히 1문항 생성):"]

        for i, item in enumerate(assessment_items, 1):
            # difficulty_band가 없거나 NULL인 경우 개념 기반 난이도 할당
            db_difficulty = item.get('difficulty_band')
            if not db_difficulty or db_difficulty == '중':
                difficulty_band = RAGUtils.get_concept_difficulty_band(item['concept_name'])
            else:
                difficulty_band = db_difficulty

            line = f"[{i}] ID={item['assessment_item_id']}, concept={item['concept_name']}, chapter={item['chapter_name']}, grade=중{item['grade']-6}, term={item['term']}학기, difficulty={difficulty_band}"
            context_lines.append(line)
            print(f"         {i}. {item['assessment_item_id']} - {item['concept_name']} (난이도: {difficulty_band})")

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

        context_block = "\n".join(context_lines)
        print(f"      [유틸] 컨텍스트 블록 완성: {len(context_lines)}줄, {len(context_block)}자")
        return context_block

    @staticmethod
    def create_cors_headers():
        """CORS 헤더 생성 (3000포트만 허용)"""
        return {
            "Content-Type": "application/json; charset=utf-8",
            "Access-Control-Allow-Origin": "http://localhost:3000",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization"
        }

    @staticmethod
    def detect_svg_requirements(concept_names):
        """
        개념명들을 분석해서 SVG가 필요한지 판단

        Args:
            concept_names (list): 개념명 리스트

        Returns:
            bool: SVG 필요 여부
        """
        all_concepts = ' '.join(concept_names).lower()

        svg_keywords = [
            '도형', '삼각형', '사각형', '원', '다각형', '기하',
            '그래프', '좌표', '직선',
            '통계', '차트', '막대', '원그래프', '히스토그램',
            '각', '넓이', '부피', '길이', '거리', '평행선', '수직선'
        ]

        requires_svg = any(keyword in all_concepts for keyword in svg_keywords)

        if requires_svg:
            matched_keywords = [kw for kw in svg_keywords if kw in all_concepts]
            print(f"      [유틸] SVG 필요 감지: {matched_keywords}")
        else:
            print(f"      [유틸] SVG 불필요 - 순수 계산/대수 문제")

        return requires_svg