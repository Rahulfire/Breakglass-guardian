"""Authentication and authorization helpers for API requests."""
from dataclasses import dataclass
from typing import Optional

from fastapi import HTTPException, Request, status
from jose import JWTError, jwt

from backend.config import settings


@dataclass(frozen=True)
class Principal:
    email: str
    roles: frozenset[str]


def decode_bearer_token(request: Request) -> Optional[Principal]:
    """Decode the configured JWT and return its identity and roles."""
    header = request.headers.get("Authorization", "")
    if not header.lower().startswith("bearer "):
        return None

    token = header[7:].strip()
    try:
        payload = jwt.decode(
            token,
            settings.auth_secret_key,
            algorithms=[settings.auth_algorithm],
        )
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    email = payload.get("sub")
    if not isinstance(email, str) or not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token has no subject",
            headers={"WWW-Authenticate": "Bearer"},
        )

    roles_claim = payload.get("roles", [])
    roles = frozenset(roles_claim if isinstance(roles_claim, list) else [roles_claim])
    return Principal(email=email.lower().strip(), roles=roles)


def require_principal(request: Request) -> Principal:
    """Require an authenticated principal when authentication is enabled."""
    if not (settings.auth_enabled or not settings.use_local_mode):
        return Principal(email="local@localhost", roles=frozenset({"admin", "internal"}))

    principal = getattr(request.state, "principal", None)
    if principal is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return principal


def require_role(*allowed_roles: str):
    """Build a dependency requiring one of the supplied roles."""
    def dependency(request: Request) -> Principal:
        principal = require_principal(request)
        if (settings.auth_enabled or not settings.use_local_mode) and not principal.roles.intersection(allowed_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return principal

    return dependency
