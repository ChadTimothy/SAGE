"""Authentication utilities for SAGE API."""

import json
import logging
from dataclasses import dataclass
from typing import Optional

from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes
from jose import jwe
from fastapi import HTTPException, Request, WebSocket, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from sage.core.config import get_settings

logger = logging.getLogger(__name__)


def _derive_nextauth_key(secret: str) -> bytes:
    """Derive encryption key from NextAuth secret using HKDF.

    NextAuth v4 derives its JWE encryption key using HKDF with:
    - Empty salt
    - Info string: "NextAuth.js Generated Encryption Key"
    - 32 bytes output (256 bits for A256GCM)
    """
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,  # 32 bytes for A256GCM
        salt=b"",  # Empty salt for NextAuth v4
        info=b"NextAuth.js Generated Encryption Key",
    )
    return hkdf.derive(secret.encode("utf-8"))


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
        # First try Authorization header
        auth_header = request.headers.get("Authorization", "")

        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]  # Strip "Bearer " prefix
            return self._verify_token(token)

        # Fall back to NextAuth session cookie (httpOnly cookie can't be read by JS)
        # NextAuth uses "next-auth.session-token" or "__Secure-next-auth.session-token"
        token = request.cookies.get("next-auth.session-token")
        if not token:
            token = request.cookies.get("__Secure-next-auth.session-token")

        if token:
            return self._verify_token(token)
        if self.auto_error:
            raise _auth_error("Not authenticated")
        return None

    def _verify_token(self, token: str) -> CurrentUser:
        """Verify encrypted JWT (JWE) from NextAuth and extract user context.

        NextAuth v4 encrypts JWT tokens using JWE (JSON Web Encryption).
        The encryption key is derived from NEXTAUTH_SECRET using HKDF.
        """
        if not self.settings.nextauth_secret:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Authentication not configured",
            )

        try:
            # Derive the encryption key using HKDF (same as NextAuth v4)
            derived_key = _derive_nextauth_key(self.settings.nextauth_secret)
            decrypted = jwe.decrypt(token, derived_key)
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

        except jwe.JWEError as e:
            logger.error(f"JWE decryption failed: {e}")
            raise _auth_error(f"Token decryption failed: {e}")
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode failed: {e}")
            raise _auth_error("Invalid token payload")
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Auth exception: {type(e).__name__}: {e}")
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

    WebSocket auth supports:
    1. Query parameter: ?token=xxx
    2. Session cookies (httpOnly cookies from NextAuth)
    """
    # First try query parameter
    token = websocket.query_params.get("token")

    # Fall back to NextAuth session cookies
    if not token:
        token = websocket.cookies.get("next-auth.session-token")
    if not token:
        token = websocket.cookies.get("__Secure-next-auth.session-token")

    if not token:
        await websocket.close(code=4001, reason="Authentication required")
        raise HTTPException(status_code=401, detail="No token provided")

    try:
        return jwt_bearer._verify_token(token)
    except HTTPException as e:
        await websocket.close(code=4001, reason=str(e.detail))
        raise
