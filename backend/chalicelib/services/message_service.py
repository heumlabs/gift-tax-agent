"""
메시지 관리 서비스

비즈니스 로직을 담당하며, Repository를 사용하여 데이터 접근
"""

import sys
from pathlib import Path
from typing import Optional

from chalicelib.models.api import (
    MessageResponse,
    MessageListResponse,
    AssistantMessageResponse,
)
from chalicelib.db.connection import get_db_session
from chalicelib.db.repositories import SessionRepository, MessageRepository

# ai 모듈을 import하기 위해 프로젝트 루트를 sys.path에 추가
ROOT_DIR = Path(__file__).resolve().parents[3]  # backend/chalicelib/services -> 3 levels up
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from ai import generate_assistant_message  # noqa: E402


class MessageService:
    """메시지 관리 서비스"""

    def __init__(self):
        """서비스 초기화"""
        pass

    def get_messages(
        self,
        session_id: str,
        client_id_hash: str,
        limit: int = 30,
        cursor: Optional[str] = None,
    ) -> MessageListResponse:
        """
        세션의 메시지 목록 조회

        Args:
            session_id: 세션 ID
            client_id_hash: 클라이언트 ID 해시
            limit: 페이지당 항목 수
            cursor: 페이지네이션 커서

        Returns:
            MessageListResponse: 메시지 목록
        """
        with get_db_session() as db:
            # 세션 권한 검증
            session_repo = SessionRepository(db)
            session = session_repo.find_by_id(session_id, client_id_hash)
            if not session:
                return MessageListResponse(messages=[], nextCursor=None)

            # 메시지 목록 조회
            message_repo = MessageRepository(db)
            messages, next_cursor = message_repo.find_all_by_session(
                session_id, limit, cursor
            )

            message_responses = [
                MessageResponse(
                    id=message.id,
                    role=message.role,
                    content=message.content,
                    metadata=message.msg_metadata,
                    createdAt=message.created_at,
                )
                for message in messages
            ]

            return MessageListResponse(
                messages=message_responses, nextCursor=next_cursor
            )

    def create_message_and_get_response(
        self, session_id: str, client_id_hash: str, content: str
    ) -> AssistantMessageResponse:
        """
        사용자 메시지를 보내고 AI 응답을 받음

        Phase 3에서 멀티턴 대화 지원을 위해 이전 메시지 조회 및
        collected_parameters 누적 로직 추가

        Args:
            session_id: 세션 ID
            client_id_hash: 클라이언트 ID 해시
            content: 사용자 메시지 내용

        Returns:
            AssistantMessageResponse: AI 응답 메시지
        """
        with get_db_session() as db:
            # 세션 권한 검증
            session_repo = SessionRepository(db)
            session = session_repo.find_by_id(session_id, client_id_hash)
            if not session:
                raise ValueError(f"Session {session_id} not found or access denied")

            message_repo = MessageRepository(db)

            # Phase 3 추가: 이전 메시지 조회 (최근 10개, 역순)
            previous_messages, _ = message_repo.find_all_by_session(
                session_id, limit=10, cursor=None
            )

            # Phase 3 추가: 마지막 assistant 메시지에서 collected_parameters 추출
            # find_all_by_session은 최신순(desc)으로 반환하므로, 첫 번째부터 순회
            previous_collected = None  # 첫 턴에서는 None → Intent 분류 실행
            for msg in previous_messages:  # 최신순으로 순회
                if msg.role == "assistant" and msg.msg_metadata:
                    # collected_parameters가 존재하면 추출 (빈 딕셔너리도 포함)
                    if "collected_parameters" in msg.msg_metadata:
                        previous_collected = msg.msg_metadata.get("collected_parameters", {})
                        break  # 가장 최근 assistant 메시지만 사용

            # 1. 사용자 메시지 저장
            message_repo.create(
                session_id=session_id, role="user", content=content, metadata=None
            )

            # 2. AI 응답 생성 (Phase 3: session_id, previous_collected_parameters 추가)
            ai_response = generate_assistant_message(
                content=content,
                session_id=session_id,
                previous_collected_parameters=previous_collected
            )

            # 3. AI 응답 메시지 저장
            assistant_message_db = message_repo.create(
                session_id=session_id,
                role="assistant",
                content=ai_response["content"],
                metadata=ai_response.get("metadata"),
            )

            assistant_message = MessageResponse(
                id=assistant_message_db.id,
                role=assistant_message_db.role,
                content=assistant_message_db.content,
                metadata=assistant_message_db.msg_metadata,
                createdAt=assistant_message_db.created_at,
            )

            return AssistantMessageResponse(assistantMessage=assistant_message)
