"""Authentication helpers for extracting tokens from requests"""
from workflows_cdk import Request
from src.utils.google_sheets import get_access_token


def get_token_from_request(request: Request) -> str:
    """
    Extract and validate OAuth token from request credentials.
    
    Args:
        request: workflows_cdk Request object
        
    Returns:
        Access token string
        
    Raises:
        ManagedError: If token is missing or invalid
    """
    return get_access_token(request.credentials)

