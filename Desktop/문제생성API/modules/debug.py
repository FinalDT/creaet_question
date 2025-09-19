def print_question_result(question_data, question_number, grade, term, topic_name):
    """생성된 문제 결과 출력"""
    from .utils import get_grade_international
    print("=" * 50)
    print(f"🎯 문제 #{question_number} 생성 완료")
    print("=" * 50)
    print(f"📝 {question_data['question_text'][:50]}...")
    print(f"📊 {question_data['question_type']} | ✅ {question_data['correct_answer']}")
    if question_data.get('choices'):
        print(f"🔍 선택지 {len(question_data['choices'])}개")
    print(f"🏷️ {get_grade_international(grade)} {term}학기 - {topic_name}")
    print("=" * 50)


def print_connection_test_header():
    """연결 테스트 헤더 출력"""
    print("=" * 50)
    print("🔍 CONNECTION TEST STARTED")
    print("=" * 50)


def print_connection_test_summary(results):
    """연결 테스트 요약 출력"""
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print("=" * 50)
    print(f"Azure OpenAI: {results['openai_status']}")
    print(f"SQL Server:   {results['sql_status']}")
    print("=" * 50)