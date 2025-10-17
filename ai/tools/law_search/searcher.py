"""Law search engine using pgvector."""

from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import text

# Backend 임포트 (DB 연결)
_PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(_PROJECT_ROOT / "backend"))

from chalicelib.db.connection import get_db_session

# AI 임포트
from ai.clients.gemini import GeminiClient
from ai.config import GeminiSettings

from .models import LawCitation, LawSearchResult


async def search_law(
    query: str,
    top_k: int = 5,
    source_filter: str | None = None,
    keyword_weight: float | None = None,
    embedding_weight: float | None = None,
    optimize_query: bool = False,
) -> LawSearchResult:
    """
    하이브리드 법령 검색 (키워드 매칭 + 임베딩 유사도)

    Args:
        query: 검색 쿼리 (예: "직계존속 증여재산 공제")
        top_k: 반환 개수 (1~10, 기본 5)
        source_filter: 법령 필터 (예: "상속세및증여세법", None이면 전체 검색)
        keyword_weight: 키워드 점수 가중치 (기본 0.3)
        embedding_weight: 임베딩 점수 가중치 (기본 0.7)
        optimize_query: LLM으로 쿼리 최적화 여부 (기본 False)

    Returns:
        LawSearchResult: 검색된 법령 인용 목록

    Example:
        >>> result = await search_law("증여재산공제", top_k=3)
        >>> result.citations[0].full_reference
        "상속세및증여세법 제53조(증여재산 공제)"

        >>> # 쿼리 최적화 사용
        >>> result = await search_law("부모님이 돈 주시면 얼마까지 세금 안내나요?", optimize_query=True)
        >>> # 내부적으로 "직계존속 증여 공제한도 증여재산공제"로 변환되어 검색
    """
    settings = GeminiSettings.from_env()
    client = GeminiClient(settings)

    # 가중치 기본값: 설정에서 가져오기
    if keyword_weight is None:
        keyword_weight = settings.law_search_keyword_weight
    if embedding_weight is None:
        embedding_weight = settings.law_search_embedding_weight

    # 쿼리 최적화 (선택적)
    original_query = query
    if optimize_query:
        from .query_optimizer import optimize_search_query
        query = await optimize_search_query(query, client)
        print(f"[Query Optimized] '{original_query}' → '{query}'")

    # 쿼리 임베딩 생성
    query_embedding = await client.generate_embedding(query)

    # 쿼리를 공백 기준으로 토큰화 (키워드 추출)
    keywords = [kw.strip() for kw in query.strip().split() if kw.strip()]

    # 테이블명: 설정에서 가져오기
    table_name = settings.law_search_table

    # 하이브리드 검색 SQL (테이블명 동적 처리)
    sql = text(f"""
        SELECT
            law_name,
            full_reference,
            content,
            source_url,
            -- 키워드 점수: full_reference와 content에서 키워드 매칭
            (
                (CASE WHEN full_reference ILIKE :kw0 THEN 2.0 ELSE 0.0 END) +
                (CASE WHEN full_reference ILIKE :kw1 THEN 2.0 ELSE 0.0 END) +
                (CASE WHEN full_reference ILIKE :kw2 THEN 2.0 ELSE 0.0 END) +
                (CASE WHEN content ILIKE :kw0 THEN 1.0 ELSE 0.0 END) +
                (CASE WHEN content ILIKE :kw1 THEN 1.0 ELSE 0.0 END) +
                (CASE WHEN content ILIKE :kw2 THEN 1.0 ELSE 0.0 END)
            ) / GREATEST(:keyword_count * 3.0, 1.0) as keyword_score,
            -- 임베딩 점수: 코사인 유사도
            1 - (embedding <=> CAST(:query_vector AS vector)) AS embedding_score,
            -- 하이브리드 최종 점수
            (
                :kw_weight * (
                    (CASE WHEN full_reference ILIKE :kw0 THEN 2.0 ELSE 0.0 END) +
                    (CASE WHEN full_reference ILIKE :kw1 THEN 2.0 ELSE 0.0 END) +
                    (CASE WHEN full_reference ILIKE :kw2 THEN 2.0 ELSE 0.0 END) +
                    (CASE WHEN content ILIKE :kw0 THEN 1.0 ELSE 0.0 END) +
                    (CASE WHEN content ILIKE :kw1 THEN 1.0 ELSE 0.0 END) +
                    (CASE WHEN content ILIKE :kw2 THEN 1.0 ELSE 0.0 END)
                ) / GREATEST(:keyword_count * 3.0, 1.0) +
                :emb_weight * (1 - (embedding <=> CAST(:query_vector AS vector)))
            ) AS score
        FROM {table_name}
        WHERE
            embedding IS NOT NULL
            AND (:filter IS NULL OR law_name LIKE :filter)
        ORDER BY score DESC
        LIMIT :top_k
    """)

    # 파라미터 준비 (최대 3개 키워드)
    params = {
        "query_vector": query_embedding,
        "filter": f"%{source_filter}%" if source_filter else None,
        "keyword_count": len(keywords),
        "kw_weight": keyword_weight,
        "emb_weight": embedding_weight,
        "top_k": min(max(top_k, 1), 10),
        "kw0": f"%{keywords[0]}%" if len(keywords) > 0 else "",
        "kw1": f"%{keywords[1]}%" if len(keywords) > 1 else "",
        "kw2": f"%{keywords[2]}%" if len(keywords) > 2 else "",
    }

    with get_db_session() as db:
        result = db.execute(sql, params)
        rows = result.fetchall()

    # Citation 포맷 변환
    citations: list[LawCitation] = []
    for row in rows:
        law_name, full_ref, content, url, kw_score, emb_score, score = row

        # Article 추출 (법령명 제거)
        article = full_ref.replace(law_name, "").strip()

        citations.append(
            LawCitation(
                law=law_name,
                article=article,
                full_reference=full_ref,
                content=content,
                url=url,
                score=float(score),
            )
        )

    return LawSearchResult(citations=citations)
