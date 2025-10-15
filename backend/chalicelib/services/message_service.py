"""
메시지 관리 서비스

비즈니스 로직을 담당하며, Repository를 사용하여 데이터 접근
현재는 Mock 데이터를 반환
"""

from typing import Optional
from datetime import datetime
from uuid import uuid4

from chalicelib.models.api import (
    MessageResponse,
    MessageListResponse,
    AssistantMessageResponse,
)


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
        # Mock AI 응답 생성
        assistant_message = MessageResponse(
            id=str(uuid4()),
            role="assistant",
            content=f"'{content}'에 대한 답변입니다. (Mock 응답)\n\n"
            "배우자로부터 증여받는 경우, 10년간 6억원까지 증여재산 공제가 적용되어 "
            "납부할 세액은 일반적으로 없습니다.",
            metadata={
                "citations": [
                    {
                        "text": "상속세및증여세법 제53조",
                        "url": "https://www.law.go.kr/...",
                    }
                ],
                "calculation": {
                    "assumptions": [
                        "거주자 간 증여",
                        "최근 10년 이내 동일인 증여 없음",
                    ],
                    "taxableAmount": 100000000,
                    "deduction": 600000000,
                    "finalTax": 0,
                },
            },
            createdAt=datetime.utcnow(),
        )

        return AssistantMessageResponse(assistantMessage=assistant_message)
