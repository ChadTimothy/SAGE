"""Authentication utilities for SAGE API.

Supports two authentication methods:
1. NextAuth JWE tokens (from web app)
2. OAuth 2.1 JWT tokens (from ChatGPT App via MCP)
"""

import json
import logging
from dataclasses import dataclass

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from fastapi import HTTPException, Request, WebSocket, status
from fastapi.security import HTTPBearer
from jose import JWTError, jwe, jwt

from sage.core.config import get_settings

logger = logging.getLogger(__name__)

# NextAuth session cookie names (standard and secure variants)
NEXTAUTH_COOKIE_NAMES = [
    "next-auth.session-token",
    "__Secure-next-auth.session-token",
]


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

    user_id: str
    learner_id: str
    email: str | None = None
    name: str | None = None
    source: str = "web"


def _verify_oauth_token(token: str) -> CurrentUser:
    """Verify an OAuth 2.1 JWT token from ChatGPT MCP."""
    settings = get_settings()
    signing_key = getattr(settings, "oauth_signing_key", None) or settings.nextauth_secret

    if not signing_key:
        raise _auth_error("OAuth signing key not configured")

    try:
        payload = jwt.decode(
            token,
            signing_key,
            algorithms=["HS256"],
            options={"verify_aud": False},
        )
    except JWTError as e:
        logger.error(f"OAuth JWT validation failed: {e}")
        raise _auth_error(f"Invalid OAuth token: {e}")

    if "sub" not in payload:
        raise _auth_error("Token missing user ID")
    if "learner_id" not in payload:
        raise _auth_error("Token missing learner ID")

    return CurrentUser(
        user_id=payload["sub"],
        learner_id=payload["learner_id"],
        email=payload.get("email"),
        name=payload.get("name"),
        source=payload.get("source", "chatgpt"),
    )


def _auth_error(detail: str) -> HTTPException:
    """Create a 401 authentication error."""
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def _get_session_cookie(cookies: dict[str, str]) -> str | None:
    """Extract NextAuth session token from cookies."""
    for name in NEXTAUTH_COOKIE_NAMES:
        if token := cookies.get(name):
            return token
    return None


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

    async def __call__(self, request: Request) -> CurrentUser | None:
        auth_header = request.headers.get("Authorization", "")

        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            return self._verify_token(token)

        token = _get_session_cookie(request.cookies)
        if token:
            return self._verify_token(token)

        if self.auto_error:
            raise _auth_error("Not authenticated")
        return None

    def _verify_token(self, token: str) -> CurrentUser:
        """Verify token and extract user context.

        Detects token format automatically:
        - JWT (3 parts): OAuth 2.1 signed token from ChatGPT MCP
        - JWE (5 parts): NextAuth encrypted token from web app
        """
        if not self.settings.nextauth_secret:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Authentication not configured",
            )

        token_parts = token.split(".")
        is_jwt_format = len(token_parts) == 3

        if is_jwt_format:
            try:
                return _verify_oauth_token(token)
            except HTTPException:
                logger.debug("OAuth JWT verification failed, trying NextAuth JWE")

        return self._verify_nextauth_token(token)

    def _verify_nextauth_token(self, token: str) -> CurrentUser:
        """Verify a NextAuth JWE token."""
        try:
            derived_key = _derive_nextauth_key(self.settings.nextauth_secret)
            decrypted = jwe.decrypt(token, derived_key)
            payload = json.loads(decrypted)
        except jwe.JWEError as e:
            logger.error(f"JWE decryption failed: {e}")
            raise _auth_error(f"Token decryption failed: {e}")
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode failed: {e}")
            raise _auth_error("Invalid token payload")

        if "sub" not in payload:
            raise _auth_error("Token missing user ID")
        if "learner_id" not in payload:
            raise _auth_error("Token missing learner ID")

        return CurrentUser(
            user_id=payload["sub"],
            learner_id=payload["learner_id"],
            email=payload.get("email"),
            name=payload.get("name"),
            source="web",
        )


# Singleton instances for dependency injection
jwt_bearer = JWTBearer()
jwt_bearer_optional = JWTBearer(auto_error=False)


async def get_current_user(request: Request) -> CurrentUser:
    """Dependency that extracts current user from JWT."""
    return await jwt_bearer(request)


async def get_current_user_optional(request: Request) -> CurrentUser | None:
    """Dependency that optionally extracts current user."""
    return await jwt_bearer_optional(request)


async def get_current_user_ws(websocket: WebSocket) -> CurrentUser:
    """Extract user from WebSocket connection."""
    token = websocket.query_params.get("token")
    if not token:
        token = _get_session_cookie(websocket.cookies)

    if not token:
        await websocket.close(code=4001, reason="Authentication required")
        raise HTTPException(status_code=401, detail="No token provided")

    try:
        return jwt_bearer._verify_token(token)
    except HTTPException as e:
        await websocket.close(code=4001, reason=str(e.detail))
        raise
