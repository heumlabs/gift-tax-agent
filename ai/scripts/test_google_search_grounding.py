"""
Google Search Grounding 기능 테스트

병렬 실행: 법령 DB 검색 + 웹 검색
"""

import asyncio
import sys
from pathlib import Path

# 프로젝트 루트 추가
_PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from ai.clients.gemini import GeminiClient
from ai.config import GeminiSettings


async def test_generate_content_with_search():
    """Google Search Grounding 단독 테스트"""
    print("=" * 60)
    print("Test 1: Google Search Grounding (단독)")
    print("=" * 60)

    settings = GeminiSettings.from_env()
    client = GeminiClient(settings)

    question = "2024년 증여세 최고 세율은 얼마인가요?"

    print(f"\n질문: {question}\n")

    response = await client.generate_content_with_search(
        system_prompt="세금 관련 질문에 정확하게 답변해주세요.",
        user_message=question
    )

    print(f"답변:\n{response.text}\n")

    if response.grounding_metadata:
        print(f"검색 쿼리: {response.grounding_metadata.web_search_queries}")
        print(f"웹 소스 개수: {len(response.grounding_metadata.grounding_chunks)}")
        print("\n출처:")
        for i, chunk in enumerate(response.grounding_metadata.grounding_chunks[:3], 1):
            print(f"  {i}. {chunk.title}")
            print(f"     {chunk.uri}")
    else:
        print("⚠️  웹 검색이 실행되지 않았습니다.")


async def test_parallel_search():
    """병렬 검색 테스트 (법령 DB + 웹 검색)"""
    print("\n" + "=" * 60)
    print("Test 2: 병렬 검색 (법령 DB + 웹 검색)")
    print("=" * 60)

    from ai.pipelines.langgraph_workflow import _search_legal_db, _search_web

    settings = GeminiSettings.from_env()
    client = GeminiClient(settings)

    question = "증여재산공제란 무엇인가요?"

    print(f"\n질문: {question}\n")
    print("⏳ 병렬 검색 시작...\n")

    import time
    start_time = time.time()

    # 병렬 실행
    legal_info, web_info = await asyncio.gather(
        _search_legal_db(question),
        _search_web(question, client)
    )

    elapsed = time.time() - start_time

    print(f"✅ 병렬 검색 완료 ({elapsed:.2f}초)\n")
    print("-" * 60)
    print("[법령 DB 결과]")
    print(legal_info if legal_info else "(검색 결과 없음)")
    print("-" * 60)
    print("[웹 검색 결과]")
    print(web_info if web_info else "(검색 결과 없음)")
    print("-" * 60)


async def main():
    print("\n🔍 Google Search Grounding 기능 테스트\n")

    try:
        # Test 1: Google Search 단독
        await test_generate_content_with_search()

        # Test 2: 병렬 검색
        await test_parallel_search()

        print("\n✅ 모든 테스트 완료!\n")

    except Exception as e:
        print(f"\n❌ 테스트 실패: {e}\n")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
