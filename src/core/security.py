from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import HTTPException, status, Depends
from starlette.requests import Request
from starlette.middleware.base import BaseHTTPMiddleware
from collections import defaultdict
import os
import time
import logging

from src.core.config import Config

security = HTTPBearer(auto_error=False)
logger = logging.getLogger(__name__)
config = Config()

# Rate limiting storage
rate_limit_storage = defaultdict(list)

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Essential security headers
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        # HSTS Header (Strict-Transport-Security)
        # This header should ONLY be set if your application is served exclusively over HTTPS.
        if os.getenv("HTTP_PROTOCOL", "http") == "https":
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'

        # Content Security Policy (CSP) for an API
        # For an API, a restrictive CSP is typically simpler and more effective,
        # This example primarily blocks content from untrusted sources.
        # You might need to adjust 'self' for specific needs if your API serves any static files or has
        # specific requirements for external content (which is unlikely for a pure API).
        # 'default-src 'self'' is a good starting point for APIs.
        # 'frame-ancestors 'none'' is redundant with X-Frame-Options but good for belt-and-suspenders.
        # It ensures that no embedding of the API into iframes is allowed.
        # response.headers['Content-Security-Policy'] = "default-src 'self'; frame-ancestors 'none'; object-src 'none';"
        
        return response

async def check_rate_limit(request_id: str = "default") -> bool:
    """Simple rate limiting implementation."""

    now = time.time()
    window_start = now - config.rate_limit_window
    
    # Clean old requests
    rate_limit_storage[request_id] = [
        req_time for req_time in rate_limit_storage[request_id] 
        if req_time > window_start
    ]
    
    # Check if under limit
    if len(rate_limit_storage[request_id]) >= config.rate_limit_requests:
        logger.warning(f"Rate limit exceeded for {request_id}")
        return False
    
    # Add current request
    rate_limit_storage[request_id].append(now)
    return True


async def validate_api_key(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Dependency to validate the API key from the Authorization header.
    Expects Authorization: Bearer <API_KEY>
    """

    if not credentials or credentials.scheme != "Bearer" or credentials.credentials != config.api_key:
        logger.warning(f"Unauthorized access attempt with credentials: {credentials}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API Key",
            headers={"WWW-Authenticate": "Bearer"},
        )
    logger.info(f"API Key validated successfully.")
    return credentials.credentials 


async def rate_limited_api_key(validated_key: str = Depends(validate_api_key)):
    """
    Dependency that enforces rate limiting based on the validated API key.
    """

    if not await check_rate_limit(validated_key): # Use the validated key as the client_id
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please wait before sending more messages."
        )
    # If successful, no return value is strictly needed for this dependency    
