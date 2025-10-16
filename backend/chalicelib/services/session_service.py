"""
세션 관리 서비스

비즈니스 로직을 담당하며, Repository를 사용하여 데이터 접근
"""

from typing import Optional

from chalicelib.models.api import SessionResponse, SessionListResponse
from chalicelib.db.connection import get_db_session
from chalicelib.db.repositories import ClientRepository, SessionRepository


class SessionService:
    """세션 관리 서비스"""

    def __init__(self):
        """서비스 초기화"""
        pass

    def create_session(self, client_id_hash: str) -> SessionResponse:
        """
        새 세션 생성

        Args:
            client_id_hash: 클라이언트 ID 해시

        Returns:
            SessionResponse: 생성된 세션 정보
        """
        with get_db_session() as db:
            # 클라이언트 존재 여부 확인 또는 생성
            client_repo = ClientRepository(db)
            client_repo.find_or_create(client_id_hash)

            # 세션 생성
            session_repo = SessionRepository(db)
            session = session_repo.create(client_id_hash)

            return SessionResponse(
                id=session.id, title=session.title, createdAt=session.created_at
            )

    def get_sessions(
        self, client_id_hash: str, limit: int = 20, cursor: Optional[str] = None
    ) -> SessionListResponse:
        """
        세션 목록 조회

        Args:
            client_id_hash: 클라이언트 ID 해시
            limit: 페이지당 항목 수
            cursor: 페이지네이션 커서

        Returns:
            SessionListResponse: 세션 목록
        """
        with get_db_session() as db:
            # 클라이언트 존재 여부 확인 또는 생성
            client_repo = ClientRepository(db)
            client_repo.find_or_create(client_id_hash)

            # 세션 목록 조회
            session_repo = SessionRepository(db)
            sessions, next_cursor = session_repo.find_all_by_client(
                client_id_hash, limit, cursor
            )

            session_responses = [
                SessionResponse(
                    id=session.id, title=session.title, createdAt=session.created_at
                )
                for session in sessions
            ]

            return SessionListResponse(
                sessions=session_responses, nextCursor=next_cursor
            )

    def update_session_title(
        self, session_id: str, client_id_hash: str, title: str
    ) -> Optional[SessionResponse]:
        """
        세션 제목 수정

        Args:
            session_id: 세션 ID
            client_id_hash: 클라이언트 ID 해시
            title: 새 제목

        Returns:
            SessionResponse: 수정된 세션 정보 또는 None
        """
        with get_db_session() as db:
            session_repo = SessionRepository(db)
            session = session_repo.update_title(session_id, client_id_hash, title)

            if session:
                return SessionResponse(
                    id=session.id, title=session.title, createdAt=session.created_at
                )
            return None

    def delete_session(self, session_id: str, client_id_hash: str) -> bool:
        """
        세션 삭제

        Args:
            session_id: 세션 ID
            client_id_hash: 클라이언트 ID 해시

        Returns:
            bool: 삭제 성공 여부
        """
        with get_db_session() as db:
            session_repo = SessionRepository(db)
            return session_repo.delete(session_id, client_id_hash)
