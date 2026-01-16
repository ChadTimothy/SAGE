"""Authentication utilities for SAGE API."""

import json
from dataclasses import dataclass
from typing import Optional

from jose.jwe import decrypt as jwe_decrypt, JWEError
from fastapi import HTTPException, Request, WebSocket, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from sage.core.config import get_settings


@dataclass
class CurrentUser:
    """Authenticated user context."""

    user_id: str  # From auth provider (sub claim)
    learner_id: str  # SAGE learner ID (linked)
    email: Optional[str] = None
    name: Optional[str] = None


def _auth_error(detail: str) -> HTTPException:
    """Create a 401 authentication error."""
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


class JWTBearer(HTTPBearer):
    """Custom JWT bearer that extracts and validates tokens."""

    def __init__(self, auto_error: bool = True):
        super().__init__(auto_error=auto_error)
        self._settings = None

    @property
    def settings(self):
        if self._settings is None:
            self._settings = get_settings()
        return self._settings

    async def __call__(self, request: Request) -> Optional[CurrentUser]:
        credentials: Optional[HTTPAuthorizationCredentials] = await super().__call__(
            request
        )
        if not credentials:
            if self.auto_error:
                raise _auth_error("Not authenticated")
            return None

        return self._verify_token(credentials.credentials)

    def _verify_token(self, token: str) -> CurrentUser:
        """Verify encrypted JWT (JWE) from NextAuth and extract user context.

        NextAuth encrypts JWT tokens using JWE (JSON Web Encryption) by default.
        We decrypt using the same NEXTAUTH_SECRET that NextAuth uses for encryption.
        """
        if not self.settings.nextauth_secret:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Authentication not configured",
            )

        try:
            secret = self.settings.nextauth_secret.encode("utf-8")
            decrypted = jwe_decrypt(token, secret)
            payload = json.loads(decrypted)

            # Validate required claims
            if "sub" not in payload:
                raise _auth_error("Token missing user ID")
            if "learner_id" not in payload:
                raise _auth_error("Token missing learner ID")

            return CurrentUser(
                user_id=payload["sub"],
                learner_id=payload["learner_id"],
                email=payload.get("email"),
                name=payload.get("name"),
            )

        except JWEError as e:
            raise _auth_error(f"Token decryption failed: {e}")
        except json.JSONDecodeError:
            raise _auth_error("Invalid token payload")
        except HTTPException:
            raise
        except Exception as e:
            raise _auth_error(f"Authentication failed: {e}")


# Singleton instances for dependency injection
jwt_bearer = JWTBearer()
jwt_bearer_optional = JWTBearer(auto_error=False)


async def get_current_user(request: Request) -> CurrentUser:
    """Dependency that extracts current user from JWT."""
    return await jwt_bearer(request)


async def get_current_user_optional(request: Request) -> Optional[CurrentUser]:
    """Dependency that optionally extracts current user."""
    return await jwt_bearer_optional(request)


async def get_current_user_ws(websocket: WebSocket) -> CurrentUser:
    """Extract user from WebSocket connection.

    WebSocket auth comes from query parameter: ?token=xxx
    """
    token = websocket.query_params.get("token")

    if not token:
        await websocket.close(code=4001, reason="Authentication required")
        raise HTTPException(status_code=401, detail="No token provided")

    try:
        return jwt_bearer._verify_token(token)
    except HTTPException as e:
        await websocket.close(code=4001, reason=str(e.detail))
        raise
