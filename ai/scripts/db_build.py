"""
법령 데이터 벡터 DB 구축 스크립트 v2 - 계층적 구조 지원

.dataset/ko-law-parser/law/*.json 파일을 파싱하여
law_sources_v2 테이블에 계층 정보와 함께 저장합니다.

주요 개선사항:
1. 계층 구조 추적 (parent_id, article_id, level)
2. 상위 계층 정보를 포함한 full_text_for_embedding 생성
3. 짧은 텍스트도 의미있는 컨텍스트 포함

Usage:
    cd /path/to/gift-tax-agent
    source .venv/bin/activate
    python -m ai.scripts.build_law_vector_db_v2
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
import sys
from pathlib import Path
from typing import Iterator

# Backend 임포트
_PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_PROJECT_ROOT / "backend"))

from chalicelib.db.connection import get_db_session
from chalicelib.models.database import LawSourceV2

# AI 임포트
from ai.clients.gemini import GeminiClient
from ai.config import GeminiSettings

logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(message)s",
)
LOGGER = logging.getLogger(__name__)


class LawNode:
    """법령 계층 노드"""

    def __init__(
        self,
        law_name: str,
        key: str,
        content: str,
        parent: LawNode | None = None,
        level: str = "article",
    ):
        self.law_name = law_name
        self.key = key  # "제53조(증여재산 공제)", "1항 배우자로부터..."
        self.content = content
        self.parent = parent
        self.level = level
        self.children: list[LawNode] = []

        # article_id 추출
        self.article_id = self._extract_article_id()

    def _extract_article_id(self) -> str | None:
        """조 번호 추출 (예: "제53조" -> "53", "제53조의2" -> "53-2")"""
        match = re.search(r"제(\d+)조(?:의(\d+))?", self.key)
        if match:
            article_num = match.group(1)
            sub_num = match.group(2)
            return f"{article_num}-{sub_num}" if sub_num else article_num

        # 부모가 있으면 부모의 article_id 상속
        if self.parent:
            return self.parent.article_id
        return None

    def get_hierarchy_path(self) -> str:
        """계층 경로 생성 (예: "제53조(증여재산 공제) > 2항")"""
        path_parts = []
        node = self
        while node:
            # 구조 키워드만 포함
            if self._is_structural_keyword(node.key):
                path_parts.insert(0, node.key)
            node = node.parent
        return " > ".join(path_parts)

    def get_full_text_for_embedding(self) -> str:
        """임베딩용 전체 텍스트 생성 (상위 계층 정보 포함)"""
        # 계층 경로 + 현재 content
        path = self.get_hierarchy_path()
        if path:
            return f"{path}\n{self.content}"
        return self.content

    def get_full_reference(self) -> str:
        """전체 참조 경로 (법령명 포함)"""
        path_parts = [self.law_name]
        node = self
        while node:
            if self._is_structural_keyword(node.key):
                path_parts.append(node.key)
            node = node.parent
        return " ".join(reversed(path_parts))

    @staticmethod
    def _is_structural_keyword(text: str) -> bool:
        """구조적 키워드인지 확인"""
        keywords = ["제", "장", "편", "절", "관", "항", "호", "목"]
        return any(kw in text for kw in keywords) and len(text) < 100


def parse_law_json_hierarchical(
    law_name: str,
    data: dict,
    source_file: str,
    parent: LawNode | None = None,
) -> Iterator[LawNode]:
    """
    계층 구조를 유지하며 재귀적 파싱

    Args:
        law_name: 법령명
        data: JSON 딕셔너리
        source_file: 원본 파일 경로
        parent: 부모 노드

    Yields:
        LawNode 객체
    """

    for key, value in data.items():
        # 레벨 판단
        level = determine_level(key)

        # 현재 노드 생성
        node = LawNode(
            law_name=law_name,
            key=key,
            content=key,  # 일단 key를 content로
            parent=parent,
            level=level,
        )

        if parent:
            parent.children.append(node)

        if isinstance(value, dict):
            if value:
                # 하위 항목이 있음 - 재귀 탐색
                yield node
                yield from parse_law_json_hierarchical(law_name, value, source_file, node)
            else:
                # 리프 노드 (본문 텍스트)
                # key가 긴 텍스트라면 이것이 실제 내용
                if len(key) >= 10:
                    node.content = key
                    yield node


def determine_level(key: str) -> str:
    """키워드로 계층 레벨 판단"""
    if re.search(r"제\d+조", key):
        return "article"
    elif re.search(r"\d+항", key):
        return "paragraph"
    elif re.search(r"\d+호", key):
        return "item"
    elif re.search(r"[가-힣]목", key):
        return "subitem"
    else:
        # 장, 절 등은 article로 분류
        if any(kw in key for kw in ["장", "절", "편", "관"]):
            return "article"
        return "article"  # 기본값


def compute_chunk_hash(law_name: str, full_ref: str, content: str) -> str:
    """청크 해시 생성"""
    data = f"{law_name}|{full_ref}|{content}"
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


async def main():
    """메인 실행 함수"""
    LOGGER.info("=" * 60)
    LOGGER.info("법령 벡터 DB 구축 v2 시작")
    LOGGER.info("=" * 60)

    # 설정 로드
    try:
        settings = GeminiSettings.from_env()
    except ValueError as e:
        LOGGER.error(f"환경 변수 오류: {e}")
        sys.exit(1)

    client = GeminiClient(settings)

    # 법령 파일 검색
    law_dir = _PROJECT_ROOT / ".dataset" / "ko-law-parser" / "law"
    if not law_dir.exists():
        LOGGER.error(f"법령 디렉토리를 찾을 수 없습니다: {law_dir}")
        sys.exit(1)

    # 상속세및증여세법 관련만 처리
    target_laws = [
        "상속세및증여세법.json",
        "상속세및증여세법시행령.json",
        "상속세및증여세법시행규칙.json",
    ]

    json_files = [law_dir / name for name in target_laws if (law_dir / name).exists()]
    LOGGER.info(f"처리 대상 법령: {len(json_files)}개")

    total_inserted = 0
    total_skipped = 0

    # 파일별 처리
    for json_file in json_files:
        law_name = json_file.stem
        LOGGER.info("")
        LOGGER.info(f"📖 처리 중: {law_name}")

        # JSON 로드
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            LOGGER.error(f"  ❌ JSON 로드 실패: {e}")
            continue

        # 계층 구조 파싱
        nodes = list(parse_law_json_hierarchical(law_name, data, str(json_file)))
        LOGGER.info(f"  ✓ {len(nodes)}개 노드 파싱 완료")

        if not nodes:
            LOGGER.warning(f"  ⚠️  노드가 없어 스킵합니다.")
            continue

        # 배치별 임베딩 및 INSERT
        batch_size = settings.embedding_batch_size

        # 먼저 parent_id 없이 저장할 노드들 (1차 INSERT)
        # 그 다음 parent_id 업데이트
        node_to_db_id = {}  # LawNode -> DB ID 매핑

        with get_db_session() as db:
            for i in range(0, len(nodes), batch_size):
                batch = nodes[i : i + batch_size]
                batch_num = i // batch_size + 1
                total_batches = (len(nodes) + batch_size - 1) // batch_size

                LOGGER.info(f"  🔄 배치 {batch_num}/{total_batches}: {len(batch)}개 노드 처리 중...")

                # 임베딩 생성 (full_text_for_embedding 사용)
                try:
                    texts = [node.get_full_text_for_embedding() for node in batch]
                    embeddings = await client.generate_embeddings_batch(texts)
                    LOGGER.info(f"     ✓ 임베딩 생성 완료 ({len(embeddings)}개)")
                except Exception as e:
                    LOGGER.error(f"     ❌ 임베딩 생성 실패: {e}")
                    continue

                # DB INSERT
                batch_inserted = 0
                batch_skipped = 0

                for node, embedding in zip(batch, embeddings):
                    full_ref = node.get_full_reference()
                    chunk_hash = compute_chunk_hash(law_name, full_ref, node.content)

                    # 중복 체크
                    exists = (
                        db.query(LawSourceV2)
                        .filter(LawSourceV2.chunk_hash == chunk_hash)
                        .first()
                    )

                    if exists:
                        batch_skipped += 1
                        node_to_db_id[id(node)] = exists.id
                        continue

                    # parent_id는 나중에 업데이트
                    try:
                        law_source = LawSourceV2(
                            chunk_hash=chunk_hash,
                            law_name=law_name,
                            full_reference=full_ref,
                            content=node.content,
                            parent_id=None,  # 1차에는 None
                            article_id=node.article_id,
                            level=node.level,
                            hierarchy_path=node.get_hierarchy_path(),
                            full_text_for_embedding=node.get_full_text_for_embedding(),
                            embedding=embedding,
                            source_file=str(json_file),
                            source_url=None,
                        )
                        db.add(law_source)
                        db.flush()  # ID 생성
                        node_to_db_id[id(node)] = law_source.id
                        batch_inserted += 1
                    except Exception as e:
                        LOGGER.error(f"     ❌ INSERT 실패: {e}")
                        continue

                # 커밋
                try:
                    db.commit()
                    total_inserted += batch_inserted
                    total_skipped += batch_skipped
                    LOGGER.info(f"     ✓ DB 저장 완료 (추가: {batch_inserted}, 스킵: {batch_skipped})")
                except Exception as e:
                    LOGGER.error(f"     ❌ DB 커밋 실패: {e}")
                    db.rollback()

            # 2단계: parent_id 업데이트
            LOGGER.info("  🔄 parent_id 업데이트 중...")
            update_count = 0

            for node in nodes:
                if node.parent and id(node) in node_to_db_id and id(node.parent) in node_to_db_id:
                    child_id = node_to_db_id[id(node)]
                    parent_id = node_to_db_id[id(node.parent)]

                    db.query(LawSourceV2).filter(LawSourceV2.id == child_id).update(
                        {"parent_id": parent_id}
                    )
                    update_count += 1

            try:
                db.commit()
                LOGGER.info(f"     ✓ parent_id {update_count}개 업데이트 완료")
            except Exception as e:
                LOGGER.error(f"     ❌ parent_id 업데이트 실패: {e}")
                db.rollback()

        LOGGER.info(f"  ✅ {law_name} 처리 완료")

    # 최종 결과
    LOGGER.info("")
    LOGGER.info("=" * 60)
    LOGGER.info("✅ 법령 벡터 DB v2 구축 완료")
    LOGGER.info(f"   총 추가: {total_inserted}개")
    LOGGER.info(f"   총 스킵: {total_skipped}개")
    LOGGER.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
