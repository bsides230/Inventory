from fastapi import Request, HTTPException
import jwt
from typing import Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class AuthenticatedUser:
    id: str
    external_id: str
    email: str
    display_name: str
    role: str

def _extract_token(request: Request) -> Optional[str]:
    auth = request.headers.get("Authorization")
    if not auth:
        return None
    parts = auth.split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1]
    return None

def get_optional_authenticated_user(request: Request) -> Optional[AuthenticatedUser]:
    token = _extract_token(request)
    if not token:
        return None
    try:
        from server import settings
        payload = jwt.decode(token, settings.auth_jwt_secret, algorithms=[settings.auth_jwt_algorithm])
        return AuthenticatedUser(
            id=payload["sub"],
            external_id=payload.get("external_id", payload["sub"]),
            email=payload.get("email", ""),
            display_name=payload.get("name", ""),
            role=payload.get("role", "user")
        )
    except jwt.PyJWTError as e:
        logger.warning(f"Invalid JWT token: {e}")
        return None

def get_required_authenticated_user(request: Request) -> AuthenticatedUser:
    user = get_optional_authenticated_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user
