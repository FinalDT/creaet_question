# -*- coding: utf-8 -*-
"""
RAG Orchestrator 모듈
RAG 기반 개인화 문제 생성의 전체 플로우를 조정하는 메인 컨트롤러
디버깅: 각 단계별 성공/실패 상태를 명확히 추적 가능
"""
import logging
import json
import azure.functions as func
from ...core.responses import create_success_response, create_error_response
from .rag_data_retriever import RAGDataRetriever
from .rag_question_generator import RAGQuestionGenerator
from .rag_utils import RAGUtils


class RAGOrchestrator:
    """RAG 기반 개인화 문제 생성을 총괄하는 오케스트레이터"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.data_retriever = RAGDataRetriever()
        self.question_generator = RAGQuestionGenerator()
        self.utils = RAGUtils()

    def handle_rag_personalized_generation(self, req):
        """
        RAG 기반 개인화 문제 생성 메인 핸들러

        Args:
            req: Azure Functions HTTP 요청 객체

        Returns:
            func.HttpResponse: HTTP 응답 객체
        """
        print(f"\n=== RAG 개인화 문제 생성 시작 ===")
        self.logger.info('RAG personalized question generation API called')

        try:
            # 1단계: 파라미터 검증 및 추출
            grade_validation_result = self._validate_and_extract_grade(req)
            if isinstance(grade_validation_result, func.HttpResponse):
                return grade_validation_result  # 오류 응답 반환

            grade_korean, grade = grade_validation_result
            print(f"[1단계] 파라미터 검증 완료: 중{grade_korean}학년 (국제식 {grade}학년)")

            # 2단계: Retrieval - 정답률 기반 Top-3 개념 선택
            print(f"[2단계] Retrieval - 개념 선택")
            top_concepts = self._retrieve_top_concepts(grade)
            if not top_concepts:
                return self._create_no_data_error_response(grade_korean)

            print(f"   └─ 선택된 개념 ({len(top_concepts)}개):")
            for i, concept in enumerate(top_concepts, 1):
                print(f"      {i}. {concept['primary_chapter']} (정답률: {concept['avg_correct_rate']:.3f})")

            # 3단계: Assessment ID 수집
            print(f"[3단계] Assessment ID 수집")
            assessment_items = self._collect_assessment_items(top_concepts)
            if not assessment_items:
                return self._create_no_items_error_response(grade_korean)

            print(f"   └─ 수집된 ID ({len(assessment_items)}개):")
            for i, item in enumerate(assessment_items, 1):
                print(f"      {i}. {item['assessment_item_id']} - {item['concept_name']}")

            # 4단계: Augmentation - RAG 컨텍스트 생성
            print(f"[4단계] Augmentation - 컨텍스트 블록 생성")
            context_block = self._create_context_block(assessment_items)

            # 5단계: Generation - AI 문제 생성
            print(f"[5단계] Generation - AI 문제 생성")
            generated_questions = self._generate_questions(context_block, assessment_items)
            if not generated_questions:
                return self._create_generation_error_response()

            print(f"   └─ 생성 완료: {len(generated_questions)}개 문제")

            # 6단계: 응답 생성
            print(f"[6단계] 성공 응답 생성")
            response_data = self._create_success_response_data(
                generated_questions, assessment_items, grade_korean, grade
            )

            print(f"=== RAG 개인화 문제 생성 완료 ===\n")
            return func.HttpResponse(
                json.dumps(response_data, ensure_ascii=False),
                status_code=200,
                headers=self.utils.create_cors_headers()
            )

        except Exception as e:
            print(f"[오류] RAG 프로세스 중 예외 발생: {str(e)}")
            self.logger.error(f"RAG personalized generation error: {str(e)}")

            response_data = create_error_response(
                f"내부 서버 오류: {str(e)}",
                status_code=500
            )
            return func.HttpResponse(
                json.dumps(response_data, ensure_ascii=False),
                status_code=500,
                headers=self.utils.create_cors_headers()
            )

    def _validate_and_extract_grade(self, req):
        """파라미터 검증 및 학년 추출"""
        print(f"   [파라미터] HTTP 메서드: {req.method}")

        # 학년 파라미터 추출
        grade_param = None

        if req.method == "GET":
            grade_param = req.params.get('grade')
            print(f"   [파라미터] GET에서 grade 추출: {grade_param}")
        elif req.method == "POST":
            try:
                req_body = req.get_json()
                if req_body and 'grade' in req_body:
                    grade_param = req_body.get('grade')
                    print(f"   [파라미터] POST JSON에서 grade 추출: {grade_param}")
                else:
                    grade_param = req.params.get('grade')
                    print(f"   [파라미터] POST URL에서 grade 추출: {grade_param}")
            except:
                grade_param = req.params.get('grade')
                print(f"   [파라미터] POST 파싱 실패, URL에서 grade 추출: {grade_param}")

        # 학년 파라미터 검증
        if not grade_param:
            print(f"   [파라미터] 오류: 학년 파라미터 누락")
            response_data = create_error_response(
                "학년 파라미터가 필요합니다. 예: ?grade=2",
                status_code=400
            )
            return func.HttpResponse(
                json.dumps(response_data, ensure_ascii=False),
                status_code=400,
                headers=self.utils.create_cors_headers()
            )

        # 숫자 변환
        try:
            grade_korean = int(grade_param)
        except ValueError:
            print(f"   [파라미터] 오류: 학년이 숫자가 아님 ({grade_param})")
            response_data = create_error_response(
                "학년은 숫자여야 합니다. 지원 학년: 1, 2, 3 (중학교)",
                status_code=400
            )
            return func.HttpResponse(
                json.dumps(response_data, ensure_ascii=False),
                status_code=400,
                headers=self.utils.create_cors_headers()
            )

        # 학년 범위 검증
        if grade_korean not in [1, 2, 3]:
            print(f"   [파라미터] 오류: 지원되지 않는 학년 ({grade_korean})")
            response_data = create_error_response(
                "지원되지 않는 학년입니다. 지원 학년: 1, 2, 3 (중학교)",
                status_code=400
            )
            return func.HttpResponse(
                json.dumps(response_data, ensure_ascii=False),
                status_code=400,
                headers=self.utils.create_cors_headers()
            )

        # 국제식 학년 변환 (1,2,3 → 7,8,9)
        grade = grade_korean + 6

        print(f"   [파라미터] 검증 완료: 중{grade_korean}학년 → 국제식 {grade}학년")
        return grade_korean, grade

    def _retrieve_top_concepts(self, grade):
        """정답률 기반 상위 개념 조회"""
        print(f"   [개념선택] 정답률 기반 Top-3 개념 조회 시작...")

        top_concepts = self.data_retriever.get_top_concepts_by_accuracy(grade, top_k=3)

        if not top_concepts:
            print(f"   [개념선택] 실패: 개념을 찾을 수 없음")
            return None

        print(f"   [개념선택] 성공: {len(top_concepts)}개 개념 선택됨")
        return top_concepts

    def _collect_assessment_items(self, top_concepts):
        """Assessment ID 수집"""
        print(f"   [ID수집] {len(top_concepts)}개 개념에서 6개 ID 수집 시작...")

        assessment_items = self.data_retriever.get_assessment_ids_by_concepts(top_concepts, target_count=6)

        if not assessment_items or len(assessment_items) == 0:
            print(f"   [ID수집] 실패: assessment item을 찾을 수 없음")
            return None

        print(f"   [ID수집] 성공: {len(assessment_items)}개 ID 수집됨")
        return assessment_items

    def _create_context_block(self, assessment_items):
        """RAG 컨텍스트 블록 생성"""
        print(f"   [컨텍스트] RAG 컨텍스트 블록 생성 중...")

        context_block = self.utils.create_rag_context_block(assessment_items)
        context_lines = context_block.split('\n')

        print(f"   [컨텍스트] 생성 완료: {len(context_lines)}줄")
        print(f"      샘플 내용:")
        for line in context_lines[:5]:  # 처음 5줄만 출력
            print(f"         {line}")
        if len(context_lines) > 5:
            print(f"         ... (총 {len(context_lines)}줄)")

        return context_block

    def _generate_questions(self, context_block, assessment_items):
        """AI 문제 생성"""
        print(f"   [AI생성] {len(assessment_items)}개 항목에 대한 문제 생성 시작...")

        generated_questions = self.question_generator.generate_questions_with_ai(
            context_block, assessment_items
        )

        if not generated_questions:
            print(f"   [AI생성] 실패: 문제 생성 불가")
            return None

        print(f"   [AI생성] 성공: {len(generated_questions)}개 문제 생성됨")

        # 생성된 문제들 요약 출력
        for i, question in enumerate(generated_questions, 1):
            concept = question.get('concept_name', 'N/A')
            question_text = question.get('question_text', 'N/A')[:50]
            svg_status = "있음" if question.get('svg_content') else "없음"
            print(f"      {i}. {concept}: {question_text}... (SVG: {svg_status})")

        return generated_questions

    def _create_success_response_data(self, generated_questions, assessment_items, grade_korean, grade):
        """성공 응답 데이터 생성"""
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

        print(f"   [응답생성] 성공 응답 데이터 생성 완료")
        print(f"      - 생성된 문제 수: {len(generated_questions)}개")
        print(f"      - 사용된 개념 수: {concepts_used}개")
        print(f"      - 대상 학년: 중{grade_korean}학년")

        return response_data

    def _create_no_data_error_response(self, grade_korean):
        """데이터 없음 오류 응답"""
        response_data = create_error_response(
            f"중학교 {grade_korean}학년에 대한 학습 데이터를 찾을 수 없습니다. 다른 학년을 시도해보세요. (지원 학년: 1, 2, 3)",
            status_code=404
        )
        return func.HttpResponse(
            json.dumps(response_data, ensure_ascii=False),
            status_code=404,
            headers=self.utils.create_cors_headers()
        )

    def _create_no_items_error_response(self, grade_korean):
        """assessment item 없음 오류 응답"""
        response_data = create_error_response(
            f"중학교 {grade_korean}학년의 문제 생성 데이터가 부족합니다. 다른 학년을 시도해보세요.",
            status_code=404
        )
        return func.HttpResponse(
            json.dumps(response_data, ensure_ascii=False),
            status_code=404,
            headers=self.utils.create_cors_headers()
        )

    def _create_generation_error_response(self):
        """문제 생성 실패 오류 응답"""
        response_data = create_error_response(
            "문제 생성에 실패했습니다.",
            status_code=500
        )
        return func.HttpResponse(
            json.dumps(response_data, ensure_ascii=False),
            status_code=500,
            headers=self.utils.create_cors_headers()
        )