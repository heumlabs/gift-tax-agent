"""
Repository 패턴 구현

데이터 액세스 로직을 비즈니스 로직과 분리
"""

from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import desc
from datetime import datetime

from chalicelib.models.database import Client, Session as DBSession, Message


class ClientRepository:
    """Client 테이블 접근 레이어"""

    def __init__(self, db: Session):
        self.db = db

    def find_or_create(self, client_id_hash: str) -> Client:
        """클라이언트 찾기 또는 생성"""
        client = (
            self.db.query(Client)
            .filter(Client.client_id_hash == client_id_hash)
            .first()
        )

        if not client:
            client = Client(client_id_hash=client_id_hash)
            self.db.add(client)
            self.db.commit()
            self.db.refresh(client)

        return client


class SessionRepository:
    """Session 테이블 접근 레이어"""

    def __init__(self, db: Session):
        self.db = db

    def create(self, client_id_hash: str, title: str = "새로운 상담") -> DBSession:
        """새 세션 생성"""
        session = DBSession(client_id_hash=client_id_hash, title=title)
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session

    def find_by_id(self, session_id: str, client_id_hash: str) -> Optional[DBSession]:
        """세션 ID로 조회 (클라이언트 검증 포함)"""
        return (
            self.db.query(DBSession)
            .filter(
                DBSession.id == session_id, DBSession.client_id_hash == client_id_hash
            )
            .first()
        )

    def find_all_by_client(
        self, client_id_hash: str, limit: int = 20, cursor: Optional[str] = None
    ) -> Tuple[List[DBSession], Optional[str]]:
        """클라이언트의 모든 세션 조회 (페이지네이션)"""
        query = (
            self.db.query(DBSession)
            .filter(DBSession.client_id_hash == client_id_hash)
            .order_by(desc(DBSession.created_at))
        )

        # 커서 기반 페이지네이션
        if cursor:
            cursor_session = (
                self.db.query(DBSession).filter(DBSession.id == cursor).first()
            )
            if cursor_session:
                query = query.filter(DBSession.created_at < cursor_session.created_at)

        sessions = query.limit(limit + 1).all()

        # 다음 커서 계산
        next_cursor = None
        if len(sessions) > limit:
            next_cursor = sessions[limit - 1].id
            sessions = sessions[:limit]

        return sessions, next_cursor

    def update_title(
        self, session_id: str, client_id_hash: str, title: str
    ) -> Optional[DBSession]:
        """세션 제목 업데이트"""
        session = self.find_by_id(session_id, client_id_hash)
        if session:
            session.title = title
            session.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(session)
        return session

    def delete(self, session_id: str, client_id_hash: str) -> bool:
        """세션 삭제"""
        session = self.find_by_id(session_id, client_id_hash)
        if session:
            # 연관된 메시지도 삭제 (CASCADE)
            self.db.query(Message).filter(Message.session_id == session_id).delete()
            self.db.delete(session)
            self.db.commit()
            return True
        return False


class MessageRepository:
    """Message 테이블 접근 레이어"""

    def __init__(self, db: Session):
        self.db = db

    def create(
        self, session_id: str, role: str, content: str, metadata: Optional[dict] = None
    ) -> Message:
        """새 메시지 생성"""
        message = Message(
            session_id=session_id, role=role, content=content, metadata=metadata
        )
        self.db.add(message)
        self.db.commit()
        self.db.refresh(message)
        return message

    def find_all_by_session(
        self, session_id: str, limit: int = 30, cursor: Optional[str] = None
    ) -> Tuple[List[Message], Optional[str]]:
        """세션의 모든 메시지 조회 (페이지네이션, 최신순)"""
        query = (
            self.db.query(Message)
            .filter(Message.session_id == session_id)
            .order_by(desc(Message.created_at))
        )

        # 커서 기반 페이지네이션
        if cursor:
            cursor_message = self.db.query(Message).filter(Message.id == cursor).first()
            if cursor_message:
                query = query.filter(Message.created_at < cursor_message.created_at)

        messages = query.limit(limit + 1).all()

        # 다음 커서 계산
        next_cursor = None
        if len(messages) > limit:
            next_cursor = messages[limit - 1].id
            messages = messages[:limit]

        return messages, next_cursor
