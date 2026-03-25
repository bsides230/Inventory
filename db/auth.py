from __future__ import annotations

from dataclasses import dataclass

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from db.database import get_session
from db.repositories import UserRepository

bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class AuthenticatedUser:
    id: int
    external_id: str
    email: str
    display_name: str
    role: str


def _decode_token(token: str, secret: str, algorithm: str) -> dict:
    try:
        return jwt.decode(token, secret, algorithms=[algorithm])
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication token") from exc


def get_optional_authenticated_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> AuthenticatedUser | None:
    if credentials is None:
        request.state.auth_user = None
        return None

    settings = request.app.state.settings
    claims = _decode_token(credentials.credentials, settings.auth_jwt_secret, settings.auth_jwt_algorithm)
    external_id = claims.get("sub")
    if not external_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token missing subject claim")

    email = claims.get("email") or f"{external_id}@local.invalid"
    display_name = claims.get("name") or external_id
    role = claims.get("role", "user")

    with get_session(settings.database_url) as session:
        users = UserRepository(session)
        user = users.get_by_external_id(external_id)
        if user is None:
            user = users.create(external_id=external_id, email=email, display_name=display_name)
        else:
            user.email = email
            user.display_name = display_name

        auth_user = AuthenticatedUser(
            id=user.id,
            external_id=user.external_id,
            email=user.email,
            display_name=user.display_name,
            role=role,
        )

    request.state.auth_user = auth_user
    return auth_user


def get_required_authenticated_user(user: AuthenticatedUser | None = Depends(get_optional_authenticated_user)) -> AuthenticatedUser:
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    return user
