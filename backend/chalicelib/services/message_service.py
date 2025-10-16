"""
메시지 관리 서비스

비즈니스 로직을 담당하며, Repository를 사용하여 데이터 접근
현재는 Mock 데이터를 반환
"""

import sys
from pathlib import Path
from typing import Optional
from datetime import datetime
from uuid import uuid4

from chalicelib.models.api import (
    MessageResponse,
    MessageListResponse,
    AssistantMessageResponse,
)

# ai 모듈을 import하기 위해 프로젝트 루트를 sys.path에 추가
ROOT_DIR = Path(__file__).resolve().parents[3]  # backend/chalicelib/services -> 3 levels up
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from ai import generate_assistant_message  # noqa: E402


class MessageService:
    """메시지 관리 서비스"""

    def __init__(self):
        """Mock 서비스이므로 DB 의존성 없음"""
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
        # Mock 데이터 반환
        mock_messages = [
            MessageResponse(
                id=str(uuid4()),
                role="user",
                content="안녕하세요?",
                metadata=None,
                createdAt=datetime.utcnow(),
            ),
            MessageResponse(
                id=str(uuid4()),
                role="assistant",
                content="네, 안녕하세요! 무엇을 도와드릴까요?",
                metadata={"citations": []},
                createdAt=datetime.utcnow(),
            ),
        ]

        return MessageListResponse(
            messages=mock_messages,
            nextCursor=None,  # Mock에서는 다음 페이지 없음
        )

    def create_message_and_get_response(
        self, session_id: str, client_id_hash: str, content: str
    ) -> AssistantMessageResponse:
        """
        사용자 메시지를 보내고 AI 응답을 받음

        Args:
            session_id: 세션 ID
            client_id_hash: 클라이언트 ID 해시
            content: 사용자 메시지 내용

        Returns:
            AssistantMessageResponse: AI 응답 메시지
        """
        # AI 모듈을 통해 실제 응답 생성
        ai_response = generate_assistant_message(content=content)

        assistant_message = MessageResponse(
            id=str(uuid4()),
            role="assistant",
            content=ai_response["content"],
            metadata=ai_response.get("metadata"),
            createdAt=datetime.utcnow(),
        )

        return AssistantMessageResponse(assistantMessage=assistant_message)
