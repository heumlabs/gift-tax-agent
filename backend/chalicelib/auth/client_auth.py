"""
클라이언트 ID 검증 및 해싱

x-client-id 헤더에서 UUID를 받아 SHA-256으로 해싱하여 사용
"""

import hashlib
from typing import Optional
from chalice import UnauthorizedError


def hash_client_id(client_id: str) -> str:
    """클라이언트 ID를 SHA-256으로 해싱"""
    return hashlib.sha256(client_id.encode()).hexdigest()


def get_client_id_hash(request) -> str:
    """
    요청에서 x-client-id 헤더를 가져와서 해싱

    Args:
        request: Chalice request object

    Returns:
        str: SHA-256 해시값

    Raises:
        UnauthorizedError: x-client-id 헤더가 없거나 유효하지 않을 때
    """
    headers = request.headers or {}
    client_id = headers.get("x-client-id") or headers.get("X-Client-Id")

    if not client_id:
        raise UnauthorizedError("Missing x-client-id header")

    # UUID 형식 기본 검증 (선택적)
    if len(client_id) < 10:
        raise UnauthorizedError("Invalid x-client-id format")

    return hash_client_id(client_id)


def validate_client_id_header(request) -> str:
    """
    x-client-id 헤더 검증 및 해시 반환

    데코레이터나 직접 호출용
    """
    return get_client_id_hash(request)
