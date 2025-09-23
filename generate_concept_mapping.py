# -*- coding: utf-8 -*-
"""
topic_name → concept_name 매핑 생성 스크립트 (모듈화 버전)
questions_dim의 concept_by_ai 컬럼에 매핑 결과 저장
"""
import os
import sys
import json
import logging
from modules.database import get_cached_concept_names, load_concept_names, get_sql_connection
from mapping.data_loader import get_unique_topic_names, debug_topic_info
from mapping.ai_mapper import generate_concept_mapping_with_ai, get_fallback_concept
from mapping.database_updater import update_concept_by_ai, update_concept_by_ai_batch, verify_update, get_concepts_for_knowledge_mapping, get_knowledge_tag_for_concept, update_knowledge_tag, update_knowledge_tag_batch, get_questions_with_knowledge_tag, assign_assessment_item_id, assign_assessment_item_id_fast, load_all_assessment_mappings, check_concept_completion, check_knowledge_tag_completion


def load_local_settings():
    """local.settings.json에서 환경변수 로드"""
    try:
        with open('local.settings.json', 'r', encoding='utf-8') as f:
            settings = json.load(f)
            values = settings.get('Values', {})

            for key, value in values.items():
                os.environ[key] = value

        print("✅ local.settings.json 환경변수 로드 완료")
        return True
    except Exception as e:
        print(f"❌ local.settings.json 로드 실패: {str(e)}")
        return False


def validate_environment():
    """필수 환경변수 확인"""
    required_vars = ["AOAI_ENDPOINT", "AOAI_KEY", "SQL_CONNECTION"]
    missing_vars = [var for var in required_vars if not os.environ.get(var)]

    if missing_vars:
        print("❌ 필수 환경변수가 설정되지 않았습니다.")
        print(f"필요한 변수: {', '.join(missing_vars)}")
        return False
    return True


def process_batch_mapping(topic_data_batch, concept_names, batch_num, total_batches):
    """배치 매핑 처리 (50개씩)"""
    batch_size = len(topic_data_batch)
    topic_concept_pairs = []
    success_count = 0

    print(f"🔄 배치 {batch_num}/{total_batches} 처리 중... ({batch_size}개)")

    # 배치 내 각 topic에 대해 AI 매핑
    for i, (topic_name, question_text) in enumerate(topic_data_batch, 1):
        # AI 매핑 시도
        selected_concept = generate_concept_mapping_with_ai(topic_name, question_text, concept_names)

        # AI 매핑 실패 시 폴백
        if not selected_concept:
            selected_concept = get_fallback_concept(topic_name, concept_names)

        if selected_concept:
            topic_concept_pairs.append((topic_name, selected_concept))
            print(f"   [{i:2d}/{batch_size}] {topic_name} → {selected_concept}")
            success_count += 1
        else:
            print(f"   [{i:2d}/{batch_size}] {topic_name} → 매핑실패 ❌")

    # 배치 DB 업데이트
    if topic_concept_pairs:
        affected_rows = update_concept_by_ai_batch(topic_concept_pairs)
        print(f"✅ 배치 {batch_num} DB 저장 완료: {affected_rows}행 업데이트")
    else:
        print(f"❌ 배치 {batch_num} 저장할 데이터 없음")

    return success_count


def process_knowledge_tag_mapping():
    """concept_by_ai → knowledgeTag 매핑 처리 (배치)"""
    print("\n4. [concept_by_ai] → [knowledgeTag] 매핑 시작 (배치 처리)...")
    print("-" * 60)

    # concept_by_ai가 있는 concept들 조회
    concept_data = get_concepts_for_knowledge_mapping()
    if not concept_data:
        print("❌ 매핑할 concept_by_ai 데이터가 없습니다.")
        return 0

    # concept → knowledgeTag 매핑 생성
    concept_tag_pairs = []
    success_count = 0
    total_count = len(concept_data)

    print(f"📊 총 {total_count}개 concept에 대한 knowledgeTag 조회 중...")

    for i, (concept_name, row_count) in enumerate(concept_data, 1):
        # gold에서 knowledgeTag 조회
        knowledge_tag = get_knowledge_tag_for_concept(concept_name)

        if knowledge_tag:
            concept_tag_pairs.append((concept_name, knowledge_tag))
            print(f"   [{i:3d}/{total_count}] {concept_name} → {knowledge_tag}")
            success_count += 1
        else:
            print(f"   [{i:3d}/{total_count}] {concept_name} → ❌ (tag없음)")

    # 배치 DB 업데이트
    if concept_tag_pairs:
        print(f"\n🔄 배치 업데이트 실행 중... ({len(concept_tag_pairs)}개 매핑)")
        affected_rows = update_knowledge_tag_batch(concept_tag_pairs)
        print(f"✅ knowledgeTag 배치 저장 완료: {affected_rows}행 업데이트")
    else:
        print("\n❌ 저장할 knowledgeTag 매핑이 없습니다.")

    print(f"\n🎯 knowledgeTag 매핑 완료: {success_count}/{total_count}개 성공")
    return success_count


def process_assessment_mapping_test():
    """knowledgeTag → assessmentItemID 매핑 (최적화된 테스트)"""
    print("\n5. [knowledgeTag] → [assessmentItemID] 매핑 테스트 (최적화)...")
    print("-" * 60)

    # 1. 전체 매핑 데이터 사전 로드 (1회만)
    print("📥 assessmentItemID 매핑 데이터 로딩 중...")
    try:
        all_mappings = load_all_assessment_mappings()
        print(f"🔍 load_all_assessment_mappings() 반환 결과: {type(all_mappings)}, 길이: {len(all_mappings) if all_mappings else 0}")

        if not all_mappings:
            print("❌ assessmentItemID 매핑 데이터를 로드할 수 없습니다.")
            print("🔍 빈 딕셔너리 반환됨 - 함수 내부 확인 필요")
            return 0

        # 샘플 데이터 출력
        sample_keys = list(all_mappings.keys())[:5]
        print(f"🔍 샘플 knowledgeTag들: {sample_keys}")
        for key in sample_keys:
            print(f"    {key}: {len(all_mappings[key])}개 assessmentItemID")

        print(f"✅ {len(all_mappings)}개 knowledgeTag 매핑 데이터 로드 완료")

    except Exception as e:
        print(f"❌ load_all_assessment_mappings() 에러: {str(e)}")
        return 0

    # 2. knowledgeTag가 있는 모든 문제 조회
    questions_data = get_questions_with_knowledge_tag()
    if not questions_data:
        print("❌ knowledgeTag가 있는 문제를 찾을 수 없습니다.")
        return 0

    # 3. 배치 단위로 처리
    used_items_by_tag = {}
    success_count = 0
    total_count = len(questions_data)
    batch_size = 1000

    print(f"📊 총 {total_count}개 문제를 {batch_size}개씩 배치 처리")
    print()

    for batch_start in range(0, total_count, batch_size):
        batch_end = min(batch_start + batch_size, total_count)
        batch_num = (batch_start // batch_size) + 1
        total_batches = (total_count + batch_size - 1) // batch_size

        print(f"🔄 배치 {batch_num}/{total_batches} 처리 중... ({batch_start + 1}~{batch_end})")

        batch_success = 0
        for i in range(batch_start, batch_end):
            question_id, topic_name, knowledge_tag = questions_data[i]

            # 최적화된 assessmentItemID 할당 (DB 조회 없음)
            assessment_id, reason = assign_assessment_item_id_fast(knowledge_tag, used_items_by_tag, all_mappings)

            if assessment_id:
                if (i - batch_start) < 5:  # 배치당 처음 5개만 상세 출력
                    print(f"   [{i + 1:5d}] [knowledgeTag] {knowledge_tag} → [assessmentItemID] {assessment_id} ✅")
                batch_success += 1
                success_count += 1
            else:
                if (i - batch_start) < 5:  # 실패한 경우는 항상 출력
                    print(f"   [{i + 1:5d}] [knowledgeTag] {knowledge_tag} → ❌ ({reason})")

        # 배치 결과 요약
        current_percent = (batch_end / total_count) * 100
        print(f"✅ 배치 {batch_num} 완료: {batch_success}/{batch_end - batch_start}개 성공")
        print(f"📈 전체 진행률: {current_percent:.1f}% ({batch_end}/{total_count})")
        print()

    # 최종 결과 요약
    print(f"🎯 assessmentItemID 매핑 완료: {success_count}/{total_count}개 성공 ({success_count/total_count*100:.1f}%)")

    # knowledgeTag별 사용 통계 (상위 10개만)
    print("\n📊 knowledgeTag별 사용 통계 (상위 10개):")
    sorted_tags = sorted(used_items_by_tag.items(), key=lambda x: len(x[1]), reverse=True)[:10]
    for tag, used_items in sorted_tags:
        print(f"   knowledgeTag {tag}: {len(used_items)}개 assessmentItemID 사용")

    return success_count


def print_summary_report(concept_success, concept_total, tag_success=0, tag_total=0, assessment_success=0, assessment_total=0):
    """최종 결과 요약 출력"""
    print("\n" + "=" * 60)
    print(f"🎯 concept 매핑: {concept_success}/{concept_total}개 성공 ({concept_success/concept_total*100:.1f}%)")
    if tag_total > 0:
        print(f"🎯 knowledgeTag 매핑: {tag_success}/{tag_total}개 성공 ({tag_success/tag_total*100:.1f}%)")
    if assessment_total > 0:
        print(f"🎯 assessmentItemID 매핑: {assessment_success}/{assessment_total}개 성공 ({assessment_success/assessment_total*100:.1f}%)")

    # DB 저장 결과 확인
    try:
        conn = get_sql_connection()
        if not conn:
            return

        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                COUNT(DISTINCT question_topic_name) as mapped_topics,
                COUNT(*) as total_rows,
                SUM(CASE WHEN concept_by_ai IS NOT NULL THEN 1 ELSE 0 END) as concept_rows,
                SUM(CASE WHEN knowledgeTag IS NOT NULL THEN 1 ELSE 0 END) as tag_rows
            FROM questions_dim
        """)

        result = cursor.fetchone()
        conn.close()

        if result:
            mapped_topics, total_rows, concept_rows, tag_rows = result
            print(f"📋 [questions_dim] 총 주제 수: {mapped_topics}개")
            print(f"📈 [concept_by_ai] 저장된 행: {concept_rows}행")
            print(f"📈 [knowledgeTag] 저장된 행: {tag_rows}행")

    except Exception as e:
        print(f"❌ 결과 확인 중 오류: {str(e)}")


def main():
    """메인 실행 함수"""
    print("💾 [questions_dim.topic_name] → [gold.gold_knowledgeTag.concept_name] 매핑")
    print("📌 매핑 결과를 questions_dim.concept_by_ai 컬럼에 저장")
    print("=" * 60)

    # 환경 설정 로드 및 검증
    if not load_local_settings() or not validate_environment():
        sys.exit(1)

    # 1. concept_name 목록 로드
    print("1. [gold.gold_knowledgeTag] concept_name 목록 로딩...")
    concept_names = get_cached_concept_names()
    if not concept_names:
        print("   📋 캐시에서 로드 실패, 직접 DB 조회...")
        if not load_concept_names():
            print("❌ concept_name 목록을 가져올 수 없습니다.")
            return
        concept_names = get_cached_concept_names()

    print(f"   ✅ [gold.gold_knowledgeTag]에서 {len(concept_names)}개 개념 로드 완료")

    # 2. topic_name 목록 가져오기
    print("\n2. [questions_dim] topic_name 목록 가져오기...")
    topic_data = get_unique_topic_names()
    if not topic_data:
        print("❌ [questions_dim] topic_name 목록을 가져올 수 없습니다.")
        return

    # 3. concept 매핑 처리 (완료 체크)
    concept_completed, concept_done, concept_total = check_concept_completion()

    if concept_completed:
        print(f"\n3. ✅ concept 매핑 이미 완료됨 ({concept_done}/{concept_total}, {concept_done/concept_total*100:.1f}%)")
        concept_success = concept_done
    else:
        print(f"\n3. AI concept 매핑 생성 시작 (배치 처리)... ({concept_done}/{concept_total} 기존 완료)")
        print("-" * 60)

        concept_success = concept_done  # 기존 완료분 포함
        batch_size = 50

        # 아직 매핑되지 않은 topic만 필터링
        remaining_topics = []
        for topic_name, question_text in topic_data:
            # 이미 매핑된 topic인지 확인하는 로직은 복잡하므로,
            # 전체를 다시 처리하되 빠르게 스킵하도록 함
            remaining_topics.append((topic_name, question_text))

        if remaining_topics:
            # 데이터를 배치로 나누기
            batches = [remaining_topics[i:i + batch_size] for i in range(0, len(remaining_topics), batch_size)]
            total_batches = len(batches)

            print(f"📊 총 {len(remaining_topics)}개 주제를 {total_batches}개 배치로 처리")
            print()

            for batch_num, batch_data in enumerate(batches, 1):
                batch_success = process_batch_mapping(batch_data, concept_names, batch_num, total_batches)
                concept_success += batch_success

                # 진행률 표시
                processed = (batch_num - 1) * batch_size + len(batch_data)
                progress = (processed / len(remaining_topics)) * 100
                print(f"📈 전체 진행률: {progress:.1f}% ({processed}/{len(remaining_topics)})")
                print()

    # 4. knowledgeTag 매핑 처리 (완료 체크)
    tag_completed, tag_done, tag_total = check_knowledge_tag_completion()

    if tag_completed:
        print(f"\n4. ✅ knowledgeTag 매핑 이미 완료됨 ({tag_done}/{tag_total}, {tag_done/tag_total*100:.1f}%)")
        tag_success = tag_done
    else:
        tag_success = process_knowledge_tag_mapping()

    # 5. assessmentItemID 매핑 테스트
    assessment_success = process_assessment_mapping_test()
    assessment_total = len(get_questions_with_knowledge_tag())

    # 6. 결과 요약
    print_summary_report(concept_success, concept_total, tag_success, tag_total, assessment_success, assessment_total)


if __name__ == "__main__":
    main()