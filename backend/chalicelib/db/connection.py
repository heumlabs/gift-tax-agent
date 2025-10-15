"""
데이터베이스 연결 및 세션 관리

SQLAlchemy를 사용한 동기 방식으로 구현
"""

from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator

from config import settings


# pydantic-settings에서 DATABASE_URL 가져오기 (DATABASE_URL 또는 DB_* 필드 조합)
DATABASE_URL = settings.database_url

# SQLAlchemy 엔진 생성
engine = create_engine(
    DATABASE_URL,
    echo=False,  # 로깅을 위해 True로 설정 가능
    pool_pre_ping=True,  # 연결 풀링 시 연결 상태 확인
    pool_size=5,
    max_overflow=10,
)

# 세션 팩토리
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """
    데이터베이스 세션 컨텍스트 매니저

    Usage:
        with get_db_session() as db:
            result = db.query(Model).all()
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_db() -> Session:
    """
    데이터베이스 세션 직접 가져오기 (수동 관리)

    사용 후 반드시 session.close() 호출 필요
    """
    return SessionLocal()
