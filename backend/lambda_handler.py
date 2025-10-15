"""
Lambda handler for Chalice app in Container Image
"""

from app import app


def handler(event, context):
    """
    Lambda handler function that invokes the Chalice app
    """
    return app(event, context)
