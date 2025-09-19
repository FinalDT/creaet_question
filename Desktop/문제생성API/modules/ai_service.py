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

    svg_instructions = ""
    if include_svg:
        svg_instructions = """
    SVG 도형 생성 지침:
    - 기하 문제의 경우 정확한 SVG 코드를 생성하세요
    - 교육용으로 적합한 깔끔한 스타일 (선 굵기, 색상 등)
    - 길이, 각도, 좌표 등을 명확히 표시
    - SVG 크기는 300x200 이내로 제한
    - 검은색 선 (#000), 회색 채우기 (#f0f0f0) 권장
    """

    if include_svg:
        response_format = f"""
    응답 형식 (JSON):
    {{
        "question_text": "문제 내용 (LaTeX 수식 포함)",
        "question_type": "{question_type}",
        "choices": ["① 선택지1", "② 선택지2", "③ 선택지3", "④ 선택지4", "⑤ 선택지5"] (선택형인 경우만),
        "correct_answer": "정답 (①~⑤ 또는 숫자/식)",
        "answer_explanation": "상세한 풀이 과정 (LaTeX 수식 포함)",
        "svg_code": "<svg>...</svg> (도형이 필요한 문제인 경우만)"
    }}
    """
    else:
        response_format = f"""
    응답 형식 (JSON):
    {{
        "question_text": "문제 내용 (LaTeX 수식 포함)",
        "question_type": "{question_type}",
        "choices": ["① 선택지1", "② 선택지2", "③ 선택지3", "④ 선택지4", "⑤ 선택지5"] (선택형인 경우만),
        "correct_answer": "정답 (①~⑤ 또는 숫자/식)",
        "answer_explanation": "상세한 풀이 과정 (LaTeX 수식 포함)"
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