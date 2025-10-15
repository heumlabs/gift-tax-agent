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


class Source(SQLModel, table=True):
    """RAG 시스템이 참조할 법령, 예규 등 원문 데이터"""

    __tablename__ = "sources"

    id: Optional[int] = Field(default=None, primary_key=True)
    document_name: str = Field(
        max_length=255, nullable=False, description="원본 문서 제목"
    )
    article_info: Optional[str] = Field(
        default=None, max_length=255, description="관련 조항 정보"
    )
    url: Optional[str] = Field(default=None, max_length=2048, description="원문 링크")
    content: str = Field(nullable=False, description="분할된 텍스트 원문")
    embedding: Optional[list] = Field(
        default=None,
        sa_column=Column(Vector(768), nullable=True),
        description="content를 벡터로 변환한 임베딩 값",
    )
    last_updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        nullable=False,
        sa_column_kwargs={"server_default": text("now()")},
    )

    __table_args__ = (
        Index("idx_sources_document", "document_name"),
        Index("idx_sources_embedding", "embedding", postgresql_using="ivfflat"),
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
