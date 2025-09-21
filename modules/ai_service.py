import os
import json
import logging
from openai import AzureOpenAI


def get_openai_client():
    """Azure OpenAI 클라이언트 초기화"""
    return AzureOpenAI(
        api_key=os.environ["AOAI_KEY"],
        api_version="2024-02-01",
        azure_endpoint=os.environ["AOAI_ENDPOINT"]
    )


def create_question_prompt(grade, term, topic_name, question_type, difficulty, existing_questions, generated_problems=[], include_svg=False):
    """문제 생성용 프롬프트 작성"""
    from .utils import get_grade_description

    # AI가 스스로 판단해서 SVG 생성하도록 지침 제공
    svg_instructions = """

    다음 경우에는 반드시 SVG를 생성하세요:
    - 삼각형, 사각형, 원 등 구체적인 도형이 나오는 기하 문제
    - 일차함수, 이차함수의 그래프를 그리거나 해석하는 문제
    - 좌표평면에서 점의 위치나 거리를 구하는 문제
    - 막대그래프, 원그래프 등 통계 차트 관련 문제
    - 각도, 길이, 넓이 등을 시각적으로 확인해야 하는 문제
    
    SVG 생성 기준:
    - 위 유형의 문제라면 적극적으로 SVG 생성
    - 학생의 이해를 돕는 시각적 자료 제공
    
    SVG 사양:
    - 크기: width="300" height="200" 
    - 스타일: 검은색 선(#000), 회색 채우기(#f0f0f0), Arial 12px
    - 중요 수치와 라벨 명확히 표시
    
    **중요**: 
    - 해설용 SVG는 생성하지 마세요 (문제 풀이용만)
    - 순수 계산 문제(연산, 방정식 풀이 등)만 svg_code를 null로 설정
    - 조금이라도 시각적 요소가 있다면 SVG를 생성하세요
    """

    # 항상 SVG 포함 가능한 응답 형식 사용
    response_format = f"""
    응답 형식 (JSON):
    {{
        "question_text": "문제 내용 (LaTeX 수식 포함)",
        "question_type": "{question_type}",
        "choices": ["① 선택지1", "② 선택지2", "③ 선택지3", "④ 선택지4", "⑤ 선택지5"] (선택형인 경우만),
        "correct_answer": "정답 (①~⑤ 또는 숫자/식)",
        "answer_explanation": "상세한 풀이 과정 (LaTeX 수식 포함)",
        "svg_code": "<svg>...</svg> 또는 null (문제 풀이에 시각 자료가 필요한 경우만)"
    }}
    """

    return f"""
    다음 조건에 맞는 중학교 수학 문제를 생성해주세요:
    - 학년: {grade} ({get_grade_description(grade)})
    - 학기: {term}학기
    - 주제: {topic_name}
    - 문제 유형: {question_type}
    - 난이도: {difficulty} (1=매우쉬움, 3=보통, 5=어려움)

    제약조건:
    - 명확한 정답이 있는 문제만 생성
    - 선택형의 경우 5개 선택지 (①, ②, ③, ④, ⑤)
    - 단답형의 경우 숫자나 간단한 식으로 답할 수 있는 문제
    - LaTeX 수식 사용 권장{svg_instructions}

    기존 문제 스타일 참고:
    {existing_questions}

    이미 생성된 문제들 (중복 피하기):
    {chr(10).join([f"- {p}" for p in generated_problems]) if generated_problems else "없음"}

    **중요**: 위에 나열된 문제들과 다른 새로운 문제를 생성하세요. 계수나 상수를 바꾸어 다양한 문제를 만드세요.

    {response_format}
    """


def generate_question_with_ai(client, grade, term, topic_name, question_type, difficulty, existing_questions, generated_problems=[], include_svg=False):
    """OpenAI를 사용하여 문제 생성"""
    try:
        prompt = create_question_prompt(grade, term, topic_name, question_type, difficulty, existing_questions, generated_problems, include_svg)

        response = client.chat.completions.create(
            model=os.environ["AOAI_DEPLOYMENT"],
            messages=[
                {"role": "system", "content": "당신은 한국 중학교 수학 문제 출제 전문가입니다. 교육부 교육과정에 맞는 고품질 문제를 JSON 형식으로 생성해주세요."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1200
        )

        # JSON 파싱 및 정리
        generated_content = response.choices[0].message.content.strip()

        # JSON 추출 (```json ``` 제거)
        if "```json" in generated_content:
            generated_content = generated_content.split("```json")[1].split("```")[0].strip()
        elif "```" in generated_content:
            generated_content = generated_content.split("```")[1].split("```")[0].strip()

        question_data = json.loads(generated_content)
        return question_data

    except json.JSONDecodeError as e:
        logging.error(f"JSON parsing failed: {str(e)}")
        logging.error(f"Raw AI response: {generated_content[:500]}...")
        return None
    except Exception as e:
        logging.error(f"AI question generation failed: {str(e)}")
        return None


def test_ai_connection():
    """AI 연결 테스트"""
    try:
        client = get_openai_client()
        test_response = client.chat.completions.create(
            model=os.environ["AOAI_DEPLOYMENT"],
            messages=[{"role": "user", "content": "Test"}],
            max_tokens=5
        )
        return True, "AI connection successful"
    except Exception as e:
        return False, str(e)