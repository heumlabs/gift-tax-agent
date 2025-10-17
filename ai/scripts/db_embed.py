#!/usr/bin/env python3
"""
law_sources_v3 테이블 생성 및 text-embedding-001로 재임베딩

v2 데이터를 복사하되, embedding만 text-embedding-001로 교체
"""

import asyncio
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_PROJECT_ROOT / "backend"))

from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

# AI 임포트
sys.path.insert(0, str(_PROJECT_ROOT))
from ai.clients.gemini import GeminiClient
from ai.config import GeminiSettings

load_dotenv()


def create_v3_table():
    """v2 구조를 복사해서 v3 테이블 생성"""
    db_url = f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASS')}@{os.getenv('DB_HOST')}/{os.getenv('DB_NAME')}"
    engine = create_engine(db_url)

    with engine.connect() as conn:
        # 기존 v3 테이블 삭제 (있다면)
        print("기존 v3 테이블 삭제 (있다면)...")
        conn.execute(text("DROP TABLE IF EXISTS law_sources_v3"))
        conn.commit()

        # v2 구조 복사해서 v3 생성 (데이터는 복사 안함)
        print("v3 테이블 생성 (v2 구조 복사)...")
        conn.execute(text("""
            CREATE TABLE law_sources_v3 (LIKE law_sources_v2 INCLUDING ALL)
        """))
        conn.commit()

        # v2 데이터 복사 (embedding 제외)
        print("v2 데이터 복사 중 (embedding 제외)...")
        conn.execute(text("""
            INSERT INTO law_sources_v3
                (id, law_name, full_reference, content, full_text_for_embedding,
                 source_url, chunk_hash, parent_id, article_id, level, created_at)
            SELECT
                id, law_name, full_reference, content, full_text_for_embedding,
                source_url, chunk_hash, parent_id, article_id, level, created_at
            FROM law_sources_v2
        """))
        conn.commit()

        # 통계
        result = conn.execute(text("SELECT COUNT(*) FROM law_sources_v3"))
        count = result.scalar()
        print(f"✅ v3 테이블 생성 완료: {count}개 레코드")

    engine.dispose()


async def reembed_v3():
    """v3 테이블의 모든 레코드를 text-embedding-001로 재임베딩"""

    # 설정 로드 (text-embedding-001 사용)
    settings = GeminiSettings.from_env()
    print(f"\n사용 모델: {settings.embedding_model}")
    print(f"차원: {settings.embedding_dimension}")

    client = GeminiClient(settings)

    db_url = f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASS')}@{os.getenv('DB_HOST')}/{os.getenv('DB_NAME')}"
    engine = create_engine(db_url)

    with engine.connect() as conn:
        # 전체 레코드 수
        result = conn.execute(text("SELECT COUNT(*) FROM law_sources_v3"))
        total = result.scalar()
        print(f"\n총 {total}개 레코드 재임베딩 시작...\n")

        # 배치 처리
        batch_size = settings.embedding_batch_size
        processed = 0

        while processed < total:
            # 배치 가져오기
            result = conn.execute(text(f"""
                SELECT id, full_text_for_embedding
                FROM law_sources_v3
                WHERE embedding IS NULL
                ORDER BY id
                LIMIT {batch_size}
            """))
            batch = result.fetchall()

            if not batch:
                break

            # 임베딩 생성
            texts = [row[1] for row in batch]
            ids = [row[0] for row in batch]

            try:
                embeddings = await client.generate_embeddings_batch(texts)
            except Exception as e:
                print(f"❌ 임베딩 생성 실패: {e}")
                break

            # DB 업데이트
            for id_, embedding in zip(ids, embeddings):
                embedding_str = "[" + ",".join(map(str, embedding)) + "]"
                # Use format() to avoid SQLAlchemy parameter binding conflict with ::vector cast
                sql = f"UPDATE law_sources_v3 SET embedding = '{embedding_str}'::vector WHERE id = {id_}"
                conn.execute(text(sql))

            conn.commit()
            processed += len(batch)
            print(f"진행: {processed}/{total} ({processed/total*100:.1f}%)")

    engine.dispose()
    print(f"\n✅ 재임베딩 완료!")


async def main():
    print("="*80)
    print("law_sources_v3 생성 및 text-embedding-001로 재임베딩")
    print("="*80)

    # 1. v3 테이블 생성
    create_v3_table()

    # 2. 재임베딩
    await reembed_v3()

    print("\n" + "="*80)
    print("완료!")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(main())
