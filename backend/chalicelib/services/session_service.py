"""
세션 관리 서비스

비즈니스 로직을 담당하며, Repository를 사용하여 데이터 접근
현재는 Mock 데이터를 반환
"""

from typing import List, Optional, Tuple
from datetime import datetime
from uuid import uuid4

from chalicelib.models.api import SessionResponse, SessionListResponse


class SessionService:
    """세션 관리 서비스"""

    def __init__(self):
        """Mock 서비스이므로 DB 의존성 없음"""
        pass

    def create_session(self, client_id_hash: str) -> SessionResponse:
        """
        새 세션 생성

        Args:
            client_id_hash: 클라이언트 ID 해시

        Returns:
            SessionResponse: 생성된 세션 정보
        """
        # Mock 데이터 반환
        return SessionResponse(
            id=str(uuid4()), title="새로운 상담", createdAt=datetime.utcnow()
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
        # Mock 데이터 반환
        mock_sessions = [
            SessionResponse(
                id=str(uuid4()), title="자녀 증여세 관련", createdAt=datetime.utcnow()
            ),
            SessionResponse(
                id=str(uuid4()), title="배우자 증여세 상담", createdAt=datetime.utcnow()
            ),
            SessionResponse(
                id=str(uuid4()), title="부동산 증여 문의", createdAt=datetime.utcnow()
            ),
        ]

        return SessionListResponse(
            sessions=mock_sessions,
            nextCursor=None,  # Mock에서는 다음 페이지 없음
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
        # Mock 데이터 반환
        return SessionResponse(id=session_id, title=title, createdAt=datetime.utcnow())

    def delete_session(self, session_id: str, client_id_hash: str) -> bool:
        """
        세션 삭제

        Args:
            session_id: 세션 ID
            client_id_hash: 클라이언트 ID 해시

        Returns:
            bool: 삭제 성공 여부
        """
        # Mock에서는 항상 성공
        return True
