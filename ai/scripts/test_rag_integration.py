"""RAG 통합 테스트 스크립트"""

import asyncio
from datetime import date
from ai.tools.gift_tax.calculator import calculate_gift_tax_simple
from ai.pipelines.langgraph_workflow import (
    _should_include_legal_basis,
    _generate_law_search_queries,
    _format_legal_references,
)


async def test_rag_helpers():
    """RAG 헬퍼 함수 테스트"""
    print("=== RAG 헬퍼 함수 테스트 ===\n")

    # 테스트 케이스 1: 세대생략 증여
    print("1. 세대생략 증여 (할증 적용)")
    collected_params = {
        "donor_relationship": "직계존속",
        "gift_property_value": 1_000_000_000,
    }
    breakdown = {
        "is_generation_skipping": True,
        "marriage_deduction": 0,
        "childbirth_deduction": 0,
        "is_minor_recipient": False,
        "is_non_resident": False,
    }

    should_include = _should_include_legal_basis(collected_params, breakdown)
    print(f"   법령 근거 포함 여부: {should_include}")

    if should_include:
        queries = _generate_law_search_queries(collected_params, breakdown)
        print(f"   검색 쿼리: {queries}")

    print()

    # 테스트 케이스 2: 혼인공제 + 출산공제
    print("2. 혼인공제 + 출산공제")
    breakdown2 = {
        "is_generation_skipping": False,
        "marriage_deduction": 100_000_000,
        "childbirth_deduction": 100_000_000,
        "is_minor_recipient": False,
        "is_non_resident": False,
    }

    should_include2 = _should_include_legal_basis(collected_params, breakdown2)
    print(f"   법령 근거 포함 여부: {should_include2}")

    if should_include2:
        queries2 = _generate_law_search_queries(collected_params, breakdown2)
        print(f"   검색 쿼리: {queries2}")

    print()

    # 테스트 케이스 3: 일반 증여 (특례 없음)
    print("3. 일반 증여 (특례 없음)")
    breakdown3 = {
        "is_generation_skipping": False,
        "marriage_deduction": 0,
        "childbirth_deduction": 0,
        "is_minor_recipient": False,
        "is_non_resident": False,
    }

    should_include3 = _should_include_legal_basis(collected_params, breakdown3)
    print(f"   법령 근거 포함 여부: {should_include3}")
    print()


async def test_rag_search():
    """실제 RAG 검색 테스트 (DB 연결 필요)"""
    print("=== 실제 RAG 검색 테스트 ===\n")

    try:
        from ai.tools.law_search.wrapper import search_law_tool

        # 테스트 쿼리
        test_queries = [
            "직계존속 증여재산 공제",
            "세대생략 증여 할증",
            "혼인공제",
        ]

        for query in test_queries:
            print(f"검색 쿼리: '{query}'")
            try:
                result = search_law_tool(query, top_k=2)
                citations = result.get("citations", [])

                if citations:
                    print(f"  ✓ {len(citations)}건 검색됨")
                    for i, cite in enumerate(citations[:2], 1):
                        ref = cite.get("full_reference", "N/A")
                        content = cite.get("content", "")[:80]
                        print(f"    {i}. {ref}")
                        print(f"       {content}...")
                else:
                    print("  ✗ 검색 결과 없음")

            except Exception as e:
                print(f"  ✗ 검색 실패: {e}")

            print()

        # 포맷팅 테스트
        print("포맷팅 테스트:")
        result = search_law_tool("직계존속 증여재산 공제", top_k=2)
        formatted = _format_legal_references(result.get("citations", []))
        print(formatted)

    except Exception as e:
        print(f"⚠️  RAG 검색 테스트 실패: {e}")
        print("   (DB 연결이 필요합니다. 환경 변수를 확인하세요)")


async def test_synthesis_with_rag():
    """Synthesis 단계에서 RAG 통합 테스트"""
    print("\n=== Synthesis with RAG 통합 테스트 ===\n")

    # 세대생략 증여 계산 (RAG 트리거)
    result = calculate_gift_tax_simple(
        gift_date=date(2025, 1, 1),
        donor_relationship="직계존속",
        gift_property_value=1_000_000_000,
        is_generation_skipping=True,  # 세대생략 → RAG 트리거
        is_minor_recipient=False,
        is_non_resident=False,
        marriage_deduction_amount=0,
        childbirth_deduction_amount=0,
        secured_debt=0,
    )

    print("계산 결과:")
    print(f"  - 최종 세액: {result['formatted_amounts']['final_tax']}")
    print(f"  - 할증 세액: {result['formatted_amounts']['surtax']}")
    print(f"  - 세율 구간: {result['tax_bracket_info']['description']}")
    print()

    # RAG 동작 확인
    from ai.pipelines.langgraph_workflow import _synthesize_response

    collected_parameters = {
        "donor_relationship": "직계존속",
        "gift_property_value": 1_000_000_000,
        "is_generation_skipping": True,
    }

    try:
        print("Synthesis 실행 중 (RAG 포함)...")
        response = await _synthesize_response(result, collected_parameters, "gift_tax")
        print("\n생성된 응답:")
        print("-" * 80)
        print(response)
        print("-" * 80)

        # 법령 근거 포함 여부 확인
        if "법적 근거" in response or "법령" in response:
            print("\n✓ RAG 법령 근거가 응답에 포함되었습니다!")
        else:
            print("\n⚠️  법령 근거가 응답에 포함되지 않았습니다.")

    except Exception as e:
        print(f"\n✗ Synthesis 실패: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """메인 테스트 함수"""
    print("=" * 80)
    print("RAG 통합 테스트")
    print("=" * 80)
    print()

    # 1. 헬퍼 함수 테스트
    await test_rag_helpers()

    # 2. 실제 RAG 검색 테스트 (DB 연결 필요)
    print("\n" + "=" * 80)
    await test_rag_search()

    # 3. Synthesis with RAG 테스트
    print("\n" + "=" * 80)
    await test_synthesis_with_rag()

    print("\n" + "=" * 80)
    print("테스트 완료")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
