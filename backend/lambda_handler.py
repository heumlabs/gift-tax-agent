"""
Lambda handler for Chalice app in Container Image
"""

import json
from app import app


def handler(event, context):
    """
    Lambda handler function that invokes the Chalice app

    API Gateway Proxy 통합 이벤트를 Chalice가 이해할 수 있도록 변환
    """
    # API Gateway Proxy 리소스 처리
    if event.get("resource") == "/{proxy+}" and "path" in event:
        event["resource"] = event["path"]
        # requestContext도 업데이트
        if "requestContext" in event:
            event["requestContext"]["resourcePath"] = event["path"]
        # pathParameters를 None으로 설정 (Chalice가 필수로 기대함)
        event["pathParameters"] = None

    return app(event, context)
