"""
데이터베이스 모델 정의 (SQLModel)

연관 문서: docs/prd_detail/database-model.md
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import Column, CheckConstraint, Index, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel
from pgvector.sqlalchemy import Vector


class Client(SQLModel, table=True):
    """익명 사용자 식별 테이블"""

    __tablename__ = "clients"

    id: Optional[int] = Field(default=None, primary_key=True)
    client_id_hash: str = Field(
        max_length=64,
        unique=True,
        nullable=False,
        description="localStorage UUID의 SHA-256 해시값",
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        nullable=False,
        sa_column_kwargs={"server_default": text("now()")},
    )


class Session(SQLModel, table=True):
    """사용자와 AI 간의 개별 대화(세션) 정보"""

    __tablename__ = "sessions"

    id: Optional[str] = Field(
        default=None,
        primary_key=True,
        sa_column_kwargs={"server_default": text("gen_random_uuid()")},
    )
    client_id_hash: str = Field(
        max_length=64,
        nullable=False,
        foreign_key="clients.client_id_hash",
        description="clients.client_id_hash를 참조하는 외래 키",
    )
    title: str = Field(max_length=255, nullable=False, description="세션 제목")
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        nullable=False,
        sa_column_kwargs={"server_default": text("now()")},
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        nullable=False,
        sa_column_kwargs={"server_default": text("now()"), "onupdate": text("now()")},
    )

    __table_args__ = (
        Index("idx_sessions_client_created", "client_id_hash", "created_at"),
    )


class Message(SQLModel, table=True):
    """세션에 속한 개별 메시지"""

    __tablename__ = "messages"

    id: Optional[str] = Field(
        default=None,
        primary_key=True,
        sa_column_kwargs={"server_default": text("gen_random_uuid()")},
    )
    session_id: str = Field(
        nullable=False, foreign_key="sessions.id", description="메시지가 속한 세션 ID"
    )
    role: str = Field(max_length=16, description="메시지 발신자 (user 또는 assistant)")
    content: str = Field(description="메시지 본문")
    msg_metadata: Optional[dict] = Field(
        default=None,
        sa_column=Column("metadata", JSONB, nullable=True),
        description="추가 정보 (인용, 계산 결과 등)",
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        nullable=False,
        sa_column_kwargs={"server_default": text("now()")},
    )

    __table_args__ = (
        CheckConstraint("role IN ('user', 'assistant')", name="check_role"),
        Index("idx_messages_session_created", "session_id", "created_at"),
    )


class LawSource(SQLModel, table=True):
    """법령과 예규 전문을 벡터 스토어로 관리"""

    __tablename__ = "law_sources"

    id: Optional[int] = Field(default=None, primary_key=True)
    chunk_hash: str = Field(
        max_length=64,
        unique=True,
        nullable=False,
        description="중복 방지를 위한 SHA-256 해시",
    )
    law_name: str = Field(nullable=False, description="법령 이름 (예: 상속세및증여세법)")
    full_reference: str = Field(
        nullable=False, description="전체 인용 경로 (예: 제1편 제2장 제53조)"
    )
    content: str = Field(nullable=False, description="분할된 텍스트 원문 (500자 내외)")
    embedding: Optional[list] = Field(
        default=None,
        sa_column=Column(Vector(768), nullable=True),
        description="content 임베딩",
    )
    source_url: Optional[str] = Field(
        default=None, max_length=2048, description="법제처 등 원문 링크"
    )
    source_file: Optional[str] = Field(
        default=None, max_length=512, description="원본 텍스트 파일 경로"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        nullable=False,
        sa_column_kwargs={"server_default": text("now()")},
    )

    __table_args__ = (
        Index("idx_law_sources_law_ref", "law_name", "full_reference"),
        Index("idx_law_sources_embedding", "embedding", postgresql_using="hnsw"),
    )


class LawSourceV2(SQLModel, table=True):
    """법령 벡터 스토어 v2 - 계층적 구조 지원"""

    __tablename__ = "law_sources_v2"

    id: Optional[int] = Field(default=None, primary_key=True)
    chunk_hash: str = Field(
        max_length=64,
        unique=True,
        nullable=False,
        description="중복 방지를 위한 SHA-256 해시",
    )

    # 기본 정보
    law_name: str = Field(nullable=False, description="법령 이름 (예: 상속세및증여세법)")
    full_reference: str = Field(
        nullable=False, description="전체 인용 경로 (예: 상속세및증여세법 제53조(증여재산 공제) 1항)"
    )
    content: str = Field(nullable=False, description="해당 계층의 원문 텍스트")

    # 계층 정보 (v2 신규)
    parent_id: Optional[int] = Field(
        default=None,
        foreign_key="law_sources_v2.id",
        description="부모 조문 ID (self-reference)",
    )
    article_id: Optional[str] = Field(
        default=None,
        max_length=50,
        description="조 단위 그룹 ID (예: '53', '53-2')",
    )
    level: Optional[str] = Field(
        default=None,
        max_length=20,
        description="계층 레벨 (article/paragraph/item/subitem)",
    )
    hierarchy_path: Optional[str] = Field(
        default=None,
        description="계층 경로 (예: '제53조(증여재산 공제) > 2항')",
    )

    # 임베딩 (v2 개선)
    full_text_for_embedding: Optional[str] = Field(
        default=None,
        description="임베딩용 전체 텍스트 (상위 계층 정보 포함)",
    )
    embedding: Optional[list] = Field(
        default=None,
        sa_column=Column(Vector(768), nullable=True),
        description="full_text_for_embedding의 임베딩",
    )

    # 메타데이터
    source_url: Optional[str] = Field(
        default=None, max_length=2048, description="법제처 등 원문 링크"
    )
    source_file: Optional[str] = Field(
        default=None, max_length=512, description="원본 JSON 파일 경로"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        nullable=False,
        sa_column_kwargs={"server_default": text("now()")},
    )

    __table_args__ = (
        Index("idx_law_sources_v2_parent", "parent_id"),
        Index("idx_law_sources_v2_article", "article_id"),
        Index("idx_law_sources_v2_level", "level"),
        Index("idx_law_sources_v2_law_ref", "law_name", "full_reference"),
        Index(
            "idx_law_sources_v2_embedding",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )


class KnowledgeSource(SQLModel, table=True):
    """법령 외 Q&A, 사례집 등 보조 지식을 저장"""

    __tablename__ = "knowledge_sources"

    id: Optional[int] = Field(default=None, primary_key=True)
    chunk_hash: str = Field(
        max_length=64,
        unique=True,
        nullable=False,
        description="중복 방지를 위한 SHA-256 해시",
    )
    source_type: str = Field(
        max_length=50, nullable=False, description="자료 유형 (qna, news, case_study)"
    )
    title: Optional[str] = Field(default=None, description="자료 제목 또는 질문")
    content: str = Field(nullable=False, description="분할된 텍스트 원문")
    embedding: Optional[list] = Field(
        default=None,
        sa_column=Column(Vector(768), nullable=True),
        description="content 임베딩",
    )
    ks_metadata: Optional[dict] = Field(
        default=None,
        sa_column=Column("metadata", JSONB, nullable=True),
        description="출처별 부가 정보 (태그, 작성일 등)",
    )
    source_url: Optional[str] = Field(
        default=None, max_length=2048, description="원문 링크"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        nullable=False,
        sa_column_kwargs={"server_default": text("now()")},
    )

    __table_args__ = (
        Index("idx_knowledge_sources_type", "source_type"),
        Index("idx_knowledge_sources_embedding", "embedding", postgresql_using="hnsw"),
        Index("idx_knowledge_sources_metadata", "metadata", postgresql_using="gin"),
    )


class TaxRuleConfig(SQLModel, table=True):
    """세율, 공제액 등 세법 규정 수치 저장"""

    __tablename__ = "tax_rule_config"

    id: Optional[int] = Field(default=None, primary_key=True)
    key: str = Field(max_length=255, nullable=False, unique=True, description="설정 키")
    value_json: dict = Field(
        sa_column=Column(JSONB, nullable=False), description="설정 값 (JSON 형식)"
    )
    effective_from: datetime = Field(nullable=False, description="효력 시작일")
    effective_to: Optional[datetime] = Field(default=None, description="효력 종료일")
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        nullable=False,
        sa_column_kwargs={"server_default": text("now()")},
    )
