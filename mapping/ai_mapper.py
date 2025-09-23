# -*- coding: utf-8 -*-
"""
AI 기반 매핑 생성
"""
import os
import logging
import json
from modules.ai_service import get_openai_client
from modules.database import get_cached_concept_names


def create_mapping_prompt(topic_name, question_text, concept_names):
    """매핑용 AI 프롬프트 생성 (간소화)"""
    return f"""
주제: {topic_name}

다음 개념 중 가장 적합한 것을 선택하세요:
{chr(10).join([f"- {concept}" for concept in concept_names])}

응답: 선택한 개념명만 정확히 입력
"""


def generate_concept_mapping_with_ai(topic_name, question_text, concept_names):
    """AI를 사용해서 topic_name에 적절한 concept_name 매핑"""
    try:
        client = get_openai_client()
        prompt = create_mapping_prompt(topic_name, question_text, concept_names)

        response = client.chat.completions.create(
            model=os.environ["AOAI_DEPLOYMENT"],
            messages=[
                {"role": "system", "content": "수학 교육과정 전문가입니다. 주제를 적절한 개념에 매핑하세요."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=100
        )

        content = response.choices[0].message.content.strip()

        # 응답 정리 (간단한 텍스트 응답)
        if content.startswith('-'):
            content = content[1:].strip()
        if content.startswith('•'):
            content = content[1:].strip()

        # 선택된 개념이 목록에 있는지 확인
        if content in concept_names:
            return content
        else:
            # 부분 매칭 시도
            for concept in concept_names:
                if concept in content or content in concept:
                    return concept
            return None

    except Exception as e:
        logging.error(f"AI 매핑 생성 실패: {str(e)}")
        return None


def get_fallback_concept(topic_name, concept_names):
    """폴백 매핑 (단순 문자열 유사도)"""
    topic_lower = topic_name.lower()

    # 키워드 기반 매핑
    keyword_mapping = {
        "확률": ["확률", "경우의 수", "구슬"],
        "일차함수": ["일차함수", "그래프", "기울기"],
        "이차함수": ["이차함수", "포물선"],
        "인수분해": ["인수분해", "완전제곱"],
        "근호": ["루트", "근호", "제곱근"],
        "방정식": ["방정식", "해"],
        "부등식": ["부등식", "대소관계"]
    }

    for concept, keywords in keyword_mapping.items():
        if concept in concept_names:
            for keyword in keywords:
                if keyword in topic_lower:
                    return concept

    # 기본값 (가장 일반적인 개념)
    defaults = ["기본 도형", "수와 연산", "식의 계산"]
    for default in defaults:
        if default in concept_names:
            return default

    # 최후의 폴백
    return concept_names[0] if concept_names else "기본 도형"