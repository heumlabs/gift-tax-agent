from chalice import Chalice, CORSConfig, Response, BadRequestError, NotFoundError
from typing import Optional

from config import settings
from chalicelib.auth import get_client_id_hash
from chalicelib.services import SessionService, MessageService
from chalicelib.models.api import SessionUpdate, MessageCreate

# CORS configuration
cors_config = CORSConfig(
    allow_origin=settings.CORS_ALLOW_ORIGIN,
    allow_headers=["Content-Type", "X-Client-Id", "X-Session-Id"],
    max_age=600,
    allow_credentials=True,
)

app = Chalice(app_name="shuking")

# 서비스 인스턴스 (싱글톤 패턴)
session_service = SessionService()
message_service = MessageService()


# ===== Helper Functions =====


def get_query_param(name: str, default: Optional[str] = None) -> Optional[str]:
    """쿼리 파라미터 가져오기"""
    params = app.current_request.query_params or {}
    return params.get(name, default)


def get_query_param_int(name: str, default: int) -> int:
    """정수형 쿼리 파라미터 가져오기"""
    value = get_query_param(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        raise BadRequestError(f"Invalid {name} parameter")


# ===== Health & Info Endpoints =====


@app.route("/")
def index():
    """API 서버 정보"""
    return {"message": "Shuking API Server", "version": "0.1.0"}


@app.route("/health", methods=["GET"], cors=cors_config)
def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "environment": settings.ENVIRONMENT}


# ===== Session Endpoints =====


@app.route("/sessions", methods=["POST"], cors=cors_config)
def create_session():
    """
    POST /sessions
    새로운 대화 세션 생성
    """
    client_id_hash = get_client_id_hash(app.current_request)
    session = session_service.create_session(client_id_hash)

    return Response(
        body=session.model_dump(mode="json", by_alias=True), status_code=201
    )


@app.route("/sessions", methods=["GET"], cors=cors_config)
def get_sessions():
    """
    GET /sessions?limit=20&cursor=xxx
    해당 클라이언트의 모든 세션 목록 조회
    """
    client_id_hash = get_client_id_hash(app.current_request)
    limit = get_query_param_int("limit", 20)
    cursor = get_query_param("cursor")

    result = session_service.get_sessions(client_id_hash, limit, cursor)

    return Response(body=result.model_dump(mode="json", by_alias=True), status_code=200)


@app.route("/sessions/{session_id}", methods=["PATCH"], cors=cors_config)
def update_session(session_id: str):
    """
    PATCH /sessions/{id}
    특정 세션의 제목 수정
    """
    client_id_hash = get_client_id_hash(app.current_request)
    body = app.current_request.json_body or {}

    # 요청 검증
    try:
        update_data = SessionUpdate(**body)
    except Exception as e:
        raise BadRequestError(f"Invalid request body: {str(e)}")

    # 세션 업데이트
    session = session_service.update_session_title(
        session_id, client_id_hash, update_data.title
    )

    if not session:
        raise NotFoundError(f"Session {session_id} not found")

    return Response(
        body=session.model_dump(mode="json", by_alias=True), status_code=200
    )


@app.route("/sessions/{session_id}", methods=["DELETE"], cors=cors_config)
def delete_session(session_id: str):
    """
    DELETE /sessions/{id}
    특정 세션 삭제
    """
    client_id_hash = get_client_id_hash(app.current_request)

    success = session_service.delete_session(session_id, client_id_hash)

    if not success:
        raise NotFoundError(f"Session {session_id} not found")

    return Response(body=None, status_code=204)


# ===== Message Endpoints =====


@app.route("/sessions/{session_id}/messages", methods=["GET"], cors=cors_config)
def get_messages(session_id: str):
    """
    GET /sessions/{id}/messages?limit=30&cursor=xxx
    특정 세션의 메시지 목록 조회
    """
    client_id_hash = get_client_id_hash(app.current_request)
    limit = get_query_param_int("limit", 30)
    cursor = get_query_param("cursor")

    result = message_service.get_messages(session_id, client_id_hash, limit, cursor)

    return Response(body=result.model_dump(mode="json", by_alias=True), status_code=200)


@app.route("/sessions/{session_id}/messages", methods=["POST"], cors=cors_config)
def create_message(session_id: str):
    """
    POST /sessions/{id}/messages
    사용자 메시지를 보내고 AI의 응답을 받음
    """
    client_id_hash = get_client_id_hash(app.current_request)
    body = app.current_request.json_body or {}

    # 요청 검증
    try:
        message_data = MessageCreate(**body)
    except Exception as e:
        raise BadRequestError(f"Invalid request body: {str(e)}")

    # 메시지 생성 및 AI 응답 받기
    result = message_service.create_message_and_get_response(
        session_id, client_id_hash, message_data.content
    )

    return Response(body=result.model_dump(mode="json", by_alias=True), status_code=200)
