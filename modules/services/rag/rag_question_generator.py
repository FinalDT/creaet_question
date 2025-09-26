# -*- coding: utf-8 -*-
"""
RAG AI 문제 생성 모듈
OpenAI GPT-4를 사용한 문제 생성과 JSON 파싱 처리 전담
디버깅: AI 응답, JSON 파싱 오류, LaTeX 처리 등을 집중 분석 가능
"""
import logging
import json
import re
from ...core.ai_service import get_openai_client
from .rag_utils import RAGUtils


class RAGQuestionGenerator:
    """RAG 방식으로 AI 문제를 생성하는 클래스"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.utils = RAGUtils()

    def generate_questions_with_ai(self, context_block, assessment_items):
        """
        RAG 전용 AI 문제 생성

        Args:
            context_block (str): RAG 컨텍스트 블록
            assessment_items (list): assessment item 리스트

        Returns:
            list: 생성된 문제 리스트 또는 None
        """
        try:
            print(f"      [AI생성] RAG 문제 생성 시작: {len(assessment_items)}개 항목")

            # OpenAI 클라이언트 가져오기
            client = get_openai_client()
            if not client:
                print(f"      [AI생성] OpenAI 클라이언트 연결 실패")
                return None

            # SVG 필요 여부 판단
            concept_names = [item['concept_name'] for item in assessment_items]
            requires_svg = self.utils.detect_svg_requirements(concept_names)

            # 프롬프트 생성
            system_prompt, user_prompt = self._create_prompts(context_block, assessment_items, requires_svg)

            # AI 호출
            print(f"      [AI생성] GPT-4 모델 호출 중...")
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
            print(f"      [AI생성] AI 응답 수신 완료 (길이: {len(ai_response)} 문자)")

            # JSON 파싱 및 문제 처리
            return self._parse_and_process_questions(ai_response, assessment_items)

        except Exception as e:
            self.logger.error(f"Error generating RAG questions with AI: {str(e)}")
            print(f"      [AI생성] 전체 프로세스 오류: {str(e)}")
            return None

    def _create_prompts(self, context_block, assessment_items, requires_svg):
        """AI용 프롬프트 생성"""
        print(f"      [프롬프트] SVG 필요 여부: {requires_svg}")

        # SVG 관련 지침
        if requires_svg:
            svg_instructions = self._get_svg_instructions_required()
        else:
            svg_instructions = self._get_svg_instructions_optional()

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

        print(f"      [프롬프트] 시스템 프롬프트 길이: {len(system_prompt)} 문자")
        print(f"      [프롬프트] 사용자 프롬프트 길이: {len(user_prompt)} 문자")

        return system_prompt, user_prompt

    def _get_svg_instructions_required(self):
        """SVG가 필요한 경우의 지침"""
        return """

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

    def _get_svg_instructions_optional(self):
        """SVG가 선택적인 경우의 지침"""
        return """

SVG 생성 판단:
- 순수 계산/대수 문제: svg_content를 null로 설정
- 시각적 요소가 조금이라도 있으면: SVG 생성

SVG 사양 (필요한 경우):
- 뷰박스 사용: viewBox='0 0 300 200' width='100%' height='auto'
- 스타일: 검은색 선(stroke='#000' stroke-width='2'), 회색 채우기(fill='#f0f0f0')
- 텍스트: font-family='Arial' font-size='14'

🔴 **중요**: SVG 속성값에는 반드시 단일 인용부호(')를 사용하세요!
"""

    def _parse_and_process_questions(self, ai_response, assessment_items):
        """AI 응답 파싱 및 문제 후처리"""
        try:
            print(f"      [파싱] JSON 파싱 시작...")

            # 코드 블록 제거
            if "```json" in ai_response:
                ai_response = ai_response.split("```json")[1].split("```")[0].strip()
            elif "```" in ai_response:
                ai_response = ai_response.split("```")[1].strip()

            # LaTeX 및 SVG 처리
            safe_json_content = self._fix_json_content(ai_response)

            # JSON 파싱 시도
            try:
                parsed_questions = json.loads(safe_json_content)
                print(f"      [파싱] 1차 파싱 성공: {len(parsed_questions)}개 문제")
            except json.JSONDecodeError as e:
                print(f"      [파싱] 1차 파싱 실패: {str(e)}")
                # 백업 파싱 시도
                parsed_questions = self._backup_parse(safe_json_content, str(e))
                if not parsed_questions:
                    return None
                print(f"      [파싱] 백업 파싱 성공: {len(parsed_questions)}개 문제")

            if not isinstance(parsed_questions, list):
                print(f"      [파싱] 오류: AI 응답이 리스트 형식이 아님")
                return None

            # 문제 후처리
            return self._post_process_questions(parsed_questions, assessment_items)

        except Exception as e:
            self.logger.error(f"Error parsing AI response: {str(e)}")
            print(f"      [파싱] 파싱 중 오류: {str(e)}")
            return None

    def _fix_json_content(self, content):
        """JSON 내용 안전 처리 (LaTeX, SVG 등)"""
        print(f"      [수정] JSON 안전 처리 시작...")

        # SVG 속성의 이중 인용부호를 단일 인용부호로 변경
        svg_matches = re.findall(r'([a-zA-Z-]+)="([^"]*)"', content)
        if svg_matches:
            print(f"      [수정] SVG 속성 {len(svg_matches)}개 발견 - 단일 인용부호로 변경")
        content = re.sub(r'([a-zA-Z-]+)="([^"]*)"', r"\1='\2'", content)

        # LaTeX 백슬래시 처리
        content = self._fix_latex_backslashes(content)

        print(f"      [수정] JSON 안전 처리 완료")
        return content

    def _fix_latex_backslashes(self, content):
        """LaTeX 백슬래시 이스케이프 처리"""
        print(f"      [LaTeX] 백슬래시 처리 시작...")

        # 1. 단일 백슬래시 패턴들을 찾아서 처리
        single_backslash_patterns = [
            r'\\(\()', r'\\(\))',  # \( \)
            r'\\(overline)', r'\\(underline)',  # \overline \underline
            r'\\(frac)', r'\\(sqrt)', r'\\(text)', r'\\(mathrm)',  # 기본 명령어들
            r'\\(left)', r'\\(right)', r'\\(times)', r'\\(cdot)',
            r'\\(pi)', r'\\(alpha)', r'\\(beta)', r'\\(gamma)', r'\\(theta)',
            r'\\(phi)', r'\\(lambda)', r'\\(delta)', r'\\(omega)', r'\\(sigma)'
        ]

        processed_count = 0
        for pattern in single_backslash_patterns:
            matches = re.findall(pattern, content)
            if matches:
                processed_count += len(matches)
            # 단일 백슬래시를 이중 백슬래시로 변경
            content = re.sub(pattern, r'\\\\\\1', content)

        # 2. LaTeX 명령어들을 정확하게 이스케이프
        latex_commands = [
            'frac', 'sqrt', 'text', 'mathrm', 'times', 'cdot', 'pi', 'alpha', 'beta', 'gamma',
            'theta', 'phi', 'lambda', 'delta', 'omega', 'sigma', 'mu', 'nu', 'tau',
            'left', 'right', 'big', 'Big', 'bigg', 'Bigg', 'overline', 'underline'
        ]

        for cmd in latex_commands:
            matches = re.findall(f'\\\\\\\\{cmd}\\b', content)
            if matches:
                processed_count += len(matches)
            # \\cmd 패턴을 찾아서 \\\\cmd로 변경
            content = re.sub(f'\\\\\\\\{cmd}\\b', f'\\\\\\\\\\\\\\\\{cmd}', content)

        # 3. LaTeX 괄호 구조 처리
        bracket_matches = re.findall(r'\\\\(\(|\)|\[|\]|\{|\})', content)
        if bracket_matches:
            processed_count += len(bracket_matches)
        content = re.sub(r'\\\\(\(|\)|\[|\]|\{|\})', r'\\\\\\\\\\1', content)

        # 4. 과도한 백슬래시 정리
        excessive_backslashes = re.findall(r'\\{8,}', content)
        if excessive_backslashes:
            print(f"      [LaTeX] 과도한 백슬래시 {len(excessive_backslashes)}개 발견 - 정리")
        content = re.sub(r'\\{8,}', r'\\\\\\\\', content)

        print(f"      [LaTeX] 백슬래시 처리 완료: {processed_count}개 명령어 처리")
        return content

    def _backup_parse(self, content, error_msg):
        """백업 JSON 파싱"""
        try:
            print(f"      [백업파싱] 강화된 백업 파싱 시도...")

            # 오류 지점 분석
            if "char" in error_msg:
                char_pos = int(error_msg.split("char ")[1].split(")")[0])
                print(f"      [백업파싱] 오류 위치: {char_pos}번째 문자")

                # 문제 구간 출력
                start = max(0, char_pos - 30)
                end = min(len(content), char_pos + 30)
                problem_section = content[start:end]
                print(f"      [백업파싱] 문제 구간: {repr(problem_section)}")

            # 강제 백슬래시 처리
            backup_content = content

            # 1. 모든 단일 백슬래시를 먼저 처리
            backup_content = re.sub(r'\\(?![\\"/bfnrt])', r'\\\\', backup_content)

            # 2. 특정 문제 패턴들 강제 처리
            problematic_patterns = {
                r'\\overline': r'\\\\overline',
                r'\\overlin': r'\\\\overlin',  # 잘린 경우도 처리
                r'\\underline': r'\\\\underline',
                r'\\frac': r'\\\\frac',
                r'\\sqrt': r'\\\\sqrt',
                r'\\\(': r'\\\\(',  # \( 패턴
                r'\\\)': r'\\\\)',  # \) 패턴
            }

            for old_pattern, new_pattern in problematic_patterns.items():
                matches = re.findall(old_pattern, backup_content)
                if matches:
                    print(f"      [백업파싱] 문제 패턴 '{old_pattern}' {len(matches)}개 처리")
                backup_content = re.sub(old_pattern, new_pattern, backup_content)

            # 파싱 시도
            parsed_questions = json.loads(backup_content)
            print(f"      [백업파싱] 성공!")
            return parsed_questions

        except Exception as backup_error:
            print(f"      [백업파싱] 실패: {str(backup_error)}")
            self.logger.error(f"Backup parsing failed: {str(backup_error)}")
            return None

    def _post_process_questions(self, parsed_questions, assessment_items):
        """문제 후처리 및 메타데이터 추가"""
        print(f"      [후처리] {len(parsed_questions)}개 문제 후처리 시작...")

        final_questions = []
        for i, question in enumerate(parsed_questions):
            if question.get('skip', False):
                print(f"      [후처리] 문제 {i+1}번: AI가 스킵으로 표시")
                continue

            # 객관식 형식 검증
            if not question.get('choices') or len(question.get('choices', [])) != 4:
                print(f"      [후처리] 문제 {i+1}번: 객관식 4지 형식 아님 - 스킵")
                continue

            # assessmentItemID 매칭
            question['id'] = self.utils.find_matching_assessment_id(question, assessment_items)

            # 메타데이터 추가
            if i < len(assessment_items):
                item = assessment_items[i]
                # difficulty_band가 없거나 NULL인 경우 개념 기반 난이도 할당
                db_difficulty = item.get('difficulty_band')
                if not db_difficulty or db_difficulty == '중':
                    difficulty_band = self.utils.get_concept_difficulty_band(item['concept_name'])
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

            print(f"      [후처리] 문제 {i+1}번 완료: {question.get('concept_name', '?')}")
            final_questions.append(question)

        print(f"      [후처리] 최종 완성: {len(final_questions)}개 문제")
        return final_questions