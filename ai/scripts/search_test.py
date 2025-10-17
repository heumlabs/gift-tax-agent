#!/usr/bin/env python3
"""
법령 검색 종합 테스트 CLI 도구

사용법:
    python ai/scripts/law_search_tester.py <명령어> [옵션]

명령어:
    interactive          대화형 검색 (V3 기본, --v2로 V2 사용)
    compare <query>      V2와 V3 비교 검색
    benchmark            표준 테스트셋으로 V2/V3 성능 비교
    test <query>         단일 쿼리 상세 테스트 (키워드/임베딩 점수 분석)

옵션:
    --v2                 V2 테이블 사용 (interactive 모드)
    --top-k N            결과 개수 (기본: 5)
    --optimize           LLM 쿼리 최적화 사용

예시:
    python ai/scripts/law_search_tester.py interactive
    python ai/scripts/law_search_tester.py compare "증여재산 공제"
    python ai/scripts/law_search_tester.py benchmark
    python ai/scripts/law_search_tester.py test "배우자 증여 공제" --top-k 10
"""

import argparse
import asyncio
import sys
from pathlib import Path

from sqlalchemy import text

_PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))
sys.path.insert(0, str(_PROJECT_ROOT / "backend"))

from chalicelib.db.connection import get_db_session
from ai.clients.gemini import GeminiClient
from ai.config import GeminiSettings


# 표준 벤치마크 테스트셋 (제53조 중심)
BENCHMARK_QUERIES = [
    {"category": "조문명", "query": "제53조 증여재산 공제", "expected": "제53조(증여재산 공제)"},
    {"category": "키워드", "query": "증여재산 공제", "expected": "제53조(증여재산 공제)"},
    {"category": "키워드", "query": "직계존속 증여 공제", "expected": "제53조(증여재산 공제)"},
    {"category": "키워드", "query": "배우자 증여 공제", "expected": "제53조(증여재산 공제)"},
    {"category": "설명형", "query": "거주자가 증여를 받은 경우 공제", "expected": "제53조(증여재산 공제)"},
    {"category": "설명형", "query": "배우자 6억원 공제", "expected": "제53조(증여재산 공제)"},
    {"category": "설명형", "query": "직계존속 5천만원 공제", "expected": "제53조(증여재산 공제)"},
    {"category": "설명형", "query": "증여세 과세가액 공제", "expected": "제53조(증여재산 공제)"},
    {"category": "키워드", "query": "증여세 신고기한", "expected": "제68조"},
    {"category": "키워드", "query": "증여세율", "expected": "제26조"},
]


async def search_law(query: str, table: str = "law_sources_v3", top_k: int = 5, optimize: bool = False) -> list[dict]:
    """
    법령 검색 (하이브리드: 키워드 30% + 임베딩 70%)

    Returns:
        [{
            "full_reference": str,
            "content": str,
            "keyword_score": float,
            "embedding_score": float,
            "score": float
        }, ...]
    """
    settings = GeminiSettings.from_env()
    client = GeminiClient(settings)

    # 쿼리 최적화 (선택적)
    original_query = query
    if optimize:
        from ai.tools.law_search.query_optimizer import optimize_search_query
        query = await optimize_search_query(query, client)
        print(f"[쿼리 최적화] '{original_query}' → '{query}'")

    # 쿼리 임베딩 생성 (자동 정규화)
    query_embedding = await client.generate_embedding(query)

    # 키워드 추출
    keywords = [kw.strip() for kw in query.strip().split() if kw.strip()]

    # 하이브리드 검색 SQL
    sql = text(f"""
        SELECT
            full_reference,
            content,
            (
                (CASE WHEN full_reference ILIKE :kw0 THEN 2.0 ELSE 0.0 END) +
                (CASE WHEN full_reference ILIKE :kw1 THEN 2.0 ELSE 0.0 END) +
                (CASE WHEN full_reference ILIKE :kw2 THEN 2.0 ELSE 0.0 END) +
                (CASE WHEN content ILIKE :kw0 THEN 1.0 ELSE 0.0 END) +
                (CASE WHEN content ILIKE :kw1 THEN 1.0 ELSE 0.0 END) +
                (CASE WHEN content ILIKE :kw2 THEN 1.0 ELSE 0.0 END)
            ) / GREATEST(:keyword_count * 3.0, 1.0) as keyword_score,
            1 - (embedding <=> CAST(:query_vector AS vector)) AS embedding_score,
            (
                0.3 * (
                    (CASE WHEN full_reference ILIKE :kw0 THEN 2.0 ELSE 0.0 END) +
                    (CASE WHEN full_reference ILIKE :kw1 THEN 2.0 ELSE 0.0 END) +
                    (CASE WHEN full_reference ILIKE :kw2 THEN 2.0 ELSE 0.0 END) +
                    (CASE WHEN content ILIKE :kw0 THEN 1.0 ELSE 0.0 END) +
                    (CASE WHEN content ILIKE :kw1 THEN 1.0 ELSE 0.0 END) +
                    (CASE WHEN content ILIKE :kw2 THEN 1.0 ELSE 0.0 END)
                ) / GREATEST(:keyword_count * 3.0, 1.0) +
                0.7 * (1 - (embedding <=> CAST(:query_vector AS vector)))
            ) AS score
        FROM {table}
        WHERE embedding IS NOT NULL
        ORDER BY score DESC
        LIMIT :top_k
    """)

    params = {
        "query_vector": query_embedding,
        "keyword_count": len(keywords),
        "top_k": top_k,
        "kw0": f"%{keywords[0]}%" if len(keywords) > 0 else "",
        "kw1": f"%{keywords[1]}%" if len(keywords) > 1 else "",
        "kw2": f"%{keywords[2]}%" if len(keywords) > 2 else "",
    }

    with get_db_session() as db:
        result = db.execute(sql, params)
        rows = result.fetchall()

    return [
        {
            "full_reference": row[0],
            "content": row[1],
            "keyword_score": float(row[2]),
            "embedding_score": float(row[3]),
            "score": float(row[4]),
        }
        for row in rows
    ]


# ============================================================
# 명령어 구현
# ============================================================

async def cmd_interactive(args):
    """대화형 검색 모드"""
    table = "law_sources_v2" if args.v2 else "law_sources_v3"
    table_label = "V2 (text-embedding-004)" if args.v2 else "V3 (gemini-001 + 768D + 정규화)"

    print(f"\n{'='*100}")
    print(f"🔍 대화형 법령 검색 - {table_label}")
    print(f"{'='*100}\n")
    print("명령어:")
    print("  - 검색어 입력: 법령 검색")
    print("  - quit/exit: 종료\n")

    while True:
        try:
            query = input("검색어 > ").strip()

            if not query:
                continue

            if query.lower() in ["quit", "exit", "q"]:
                print("\n👋 종료합니다.\n")
                break

            results = await search_law(query, table=table, top_k=args.top_k, optimize=args.optimize)

            print(f"\n{'='*100}")
            print(f"🔍 '{query}' 검색 결과 ({len(results)}개)")
            print(f"{'='*100}\n")

            if not results:
                print("❌ 검색 결과가 없습니다.\n")
                continue

            for i, r in enumerate(results, 1):
                print(f"[{i}위] {r['full_reference']}")
                print(f"      점수: {r['score']:.4f} (키워드: {r['keyword_score']:.4f} | 임베딩: {r['embedding_score']:.4f})")
                content_preview = r['content'][:100].replace('\n', ' ')
                print(f"      내용: {content_preview}...")
                print()

        except KeyboardInterrupt:
            print("\n\n👋 종료합니다.\n")
            break
        except Exception as e:
            print(f"\n❌ 오류: {e}\n")


async def cmd_compare(args):
    """V2와 V3 비교 검색"""
    query = args.query

    print(f"\n{'='*100}")
    print(f"🔍 V2 vs V3 비교 검색: '{query}'")
    print(f"{'='*100}\n")

    v2_results = await search_law(query, table="law_sources_v2", top_k=args.top_k)
    v3_results = await search_law(query, table="law_sources_v3", top_k=args.top_k)

    print(f"{'순위':<6} {'V2 (text-embedding-004)':<45} {'점수':<10} {'V3 (gemini-001+정규화)':<45} {'점수':<10}")
    print("-" * 120)

    for i in range(max(len(v2_results), len(v3_results))):
        v2_ref = v2_results[i]['full_reference'][:42] if i < len(v2_results) else "-"
        v2_score = f"{v2_results[i]['score']:.4f}" if i < len(v2_results) else "-"

        v3_ref = v3_results[i]['full_reference'][:42] if i < len(v3_results) else "-"
        v3_score = f"{v3_results[i]['score']:.4f}" if i < len(v3_results) else "-"

        same = "✓" if (i < len(v2_results) and i < len(v3_results) and
                       v2_results[i]['full_reference'] == v3_results[i]['full_reference']) else ""

        print(f"{i+1}위{same:<4} {v2_ref:<45} {v2_score:<10} {v3_ref:<45} {v3_score:<10}")

    print()


async def cmd_benchmark(args):
    """벤치마크 테스트 (V2 vs V3)"""
    print(f"\n{'='*100}")
    print("📊 벤치마크 테스트: V2 vs V3")
    print(f"{'='*100}\n")

    results = []

    for i, test_case in enumerate(BENCHMARK_QUERIES, 1):
        query = test_case["query"]
        expected = test_case["expected"]

        v2_results = await search_law(query, table="law_sources_v2", top_k=10)
        v3_results = await search_law(query, table="law_sources_v3", top_k=10)

        # V2 순위
        v2_rank = None
        for rank, r in enumerate(v2_results, 1):
            if expected in r["full_reference"]:
                v2_rank = rank
                break

        # V3 순위
        v3_rank = None
        for rank, r in enumerate(v3_results, 1):
            if expected in r["full_reference"]:
                v3_rank = rank
                break

        v2_str = f"{v2_rank}위" if v2_rank else "❌"
        v3_str = f"{v3_rank}위" if v3_rank else "❌"

        if v3_rank and (not v2_rank or v3_rank < v2_rank):
            status = "🔥"
        elif v3_rank == v2_rank:
            status = "⚪"
        else:
            status = "⬇️"

        print(f"{status} [{i:2d}/{len(BENCHMARK_QUERIES)}] V2: {v2_str:6s} → V3: {v3_str:6s} | {query}")

        results.append({
            "query": query,
            "category": test_case["category"],
            "v2_rank": v2_rank,
            "v3_rank": v3_rank,
        })

    # 통계
    total = len(results)
    v2_found = sum(1 for r in results if r["v2_rank"] is not None)
    v2_top3 = sum(1 for r in results if r["v2_rank"] is not None and r["v2_rank"] <= 3)
    v3_found = sum(1 for r in results if r["v3_rank"] is not None)
    v3_top3 = sum(1 for r in results if r["v3_rank"] is not None and r["v3_rank"] <= 3)

    print(f"\n{'='*100}")
    print("📊 통계")
    print(f"{'='*100}\n")
    print(f"{'항목':<20} {'V2':<20} {'V3':<20} {'변화':<10}")
    print("-" * 80)
    print(f"{'발견율':<20} {v2_found}/{total} ({v2_found/total*100:5.1f}%){' '*5} {v3_found}/{total} ({v3_found/total*100:5.1f}%){' '*5} {'+' if v3_found > v2_found else ''}{v3_found - v2_found}")
    print(f"{'Top-3 정확도':<20} {v2_top3}/{total} ({v2_top3/total*100:5.1f}%){' '*5} {v3_top3}/{total} ({v3_top3/total*100:5.1f}%){' '*5} {'+' if v3_top3 > v2_top3 else ''}{v3_top3 - v2_top3}")
    print()


async def cmd_test(args):
    """단일 쿼리 상세 테스트"""
    query = args.query
    table = "law_sources_v2" if args.v2 else "law_sources_v3"
    table_label = "V2 (text-embedding-004)" if args.v2 else "V3 (gemini-001 + 768D + 정규화)"

    print(f"\n{'='*100}")
    print(f"🔍 상세 테스트: '{query}' - {table_label}")
    print(f"{'='*100}\n")

    results = await search_law(query, table=table, top_k=args.top_k, optimize=args.optimize)

    if not results:
        print("❌ 검색 결과가 없습니다.\n")
        return

    print(f"{'순위':<6} {'조문':<50} {'최종':<8} {'키워드':<8} {'임베딩':<8}")
    print("-" * 90)

    for i, r in enumerate(results, 1):
        ref = r['full_reference'][:47]
        print(f"{i}위    {ref:<50} {r['score']:.4f}   {r['keyword_score']:.4f}   {r['embedding_score']:.4f}")

    print()

    # 1위 상세 정보
    print(f"{'='*100}")
    print("1위 상세 정보")
    print(f"{'='*100}\n")
    top1 = results[0]
    print(f"조문: {top1['full_reference']}")
    print(f"최종 점수: {top1['score']:.4f}")
    print(f"  - 키워드 점수: {top1['keyword_score']:.4f} (가중치 30%)")
    print(f"  - 임베딩 점수: {top1['embedding_score']:.4f} (가중치 70%)")
    print(f"\n내용:\n{top1['content'][:300]}...\n")


# ============================================================
# CLI 진입점
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="법령 검색 종합 테스트 CLI 도구",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    subparsers = parser.add_subparsers(dest="command", help="명령어")

    # interactive 명령어
    interactive_parser = subparsers.add_parser("interactive", help="대화형 검색")
    interactive_parser.add_argument("--v2", action="store_true", help="V2 테이블 사용")
    interactive_parser.add_argument("--top-k", type=int, default=5, help="결과 개수 (기본: 5)")
    interactive_parser.add_argument("--optimize", action="store_true", help="LLM 쿼리 최적화 사용")

    # compare 명령어
    compare_parser = subparsers.add_parser("compare", help="V2와 V3 비교 검색")
    compare_parser.add_argument("query", help="검색어")
    compare_parser.add_argument("--top-k", type=int, default=5, help="결과 개수 (기본: 5)")

    # benchmark 명령어
    benchmark_parser = subparsers.add_parser("benchmark", help="벤치마크 테스트")

    # test 명령어
    test_parser = subparsers.add_parser("test", help="단일 쿼리 상세 테스트")
    test_parser.add_argument("query", help="검색어")
    test_parser.add_argument("--v2", action="store_true", help="V2 테이블 사용")
    test_parser.add_argument("--top-k", type=int, default=5, help="결과 개수 (기본: 5)")
    test_parser.add_argument("--optimize", action="store_true", help="LLM 쿼리 최적화 사용")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # 명령어 실행
    if args.command == "interactive":
        asyncio.run(cmd_interactive(args))
    elif args.command == "compare":
        asyncio.run(cmd_compare(args))
    elif args.command == "benchmark":
        asyncio.run(cmd_benchmark(args))
    elif args.command == "test":
        asyncio.run(cmd_test(args))


if __name__ == "__main__":
    main()
