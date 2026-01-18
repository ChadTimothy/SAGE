"""OAuth 2.1 routes for ChatGPT App authentication.

Implements:
- RFC 9728: OAuth 2.0 Protected Resource Metadata
- RFC 7591: OAuth 2.0 Dynamic Client Registration
- OAuth 2.1 Authorization Code flow with PKCE
"""

import base64
import hashlib
import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Annotated
from urllib.parse import urlencode

from fastapi import APIRouter, Form, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from jose import jwt

from sage.core.config import get_settings
from sage.api.models.oauth import (
    ClientRegistrationRequest,
    ClientRegistrationResponse,
    OAuthAuthCode,
    OAuthClient,
    OAuthMetadata,
    OAuthRefreshToken,
    ProtectedResourceMetadata,
    TokenErrorResponse,
    TokenRequest,
    TokenResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["oauth"])

# OAuth constants
SUPPORTED_SCOPES = ["learner:read", "learner:write", "session:manage"]
DEFAULT_SCOPE = " ".join(SUPPORTED_SCOPES)
AUTH_CODE_LIFETIME_MINUTES = 10
REFRESH_TOKEN_LIFETIME_DAYS = 30
CLIENT_REGISTRATION_LIFETIME_HOURS = 24
ACCESS_TOKEN_LIFETIME_SECONDS = 3600

# In-memory stores (replace with database in production)
_oauth_clients: dict[str, OAuthClient] = {}
_auth_codes: dict[str, OAuthAuthCode] = {}
_refresh_tokens: dict[str, OAuthRefreshToken] = {}


# =============================================================================
# Configuration
# =============================================================================


def _get_base_url() -> str:
    """Get the base URL for OAuth endpoints."""
    settings = get_settings()
    return getattr(settings, "oauth_base_url", "http://localhost:8000")


def _get_oauth_signing_key() -> str:
    """Get the signing key for OAuth JWTs."""
    settings = get_settings()
    key = getattr(settings, "oauth_signing_key", None)
    if not key:
        # Fall back to nextauth_secret for development
        key = settings.nextauth_secret
    if not key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="OAuth signing key not configured",
        )
    return key


# =============================================================================
# Utility Functions
# =============================================================================


def _hash_secret(value: str) -> str:
    """Create a secure hash of a secret value."""
    return hashlib.sha256(value.encode()).hexdigest()


def _verify_pkce(code_verifier: str, code_challenge: str) -> bool:
    """Verify PKCE code_verifier against code_challenge using S256 method."""
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    computed_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return secrets.compare_digest(computed_challenge, code_challenge)


def _generate_access_token(
    user_id: str,
    learner_id: str,
    scope: str,
    client_id: str,
) -> str:
    """Generate a JWT access token."""
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(seconds=ACCESS_TOKEN_LIFETIME_SECONDS)

    payload = {
        "iss": _get_base_url(),
        "sub": user_id,
        "aud": client_id,
        "learner_id": learner_id,
        "scope": scope,
        "source": "chatgpt",
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
    }

    return jwt.encode(payload, _get_oauth_signing_key(), algorithm="HS256")


def _generate_refresh_token() -> str:
    """Generate a secure refresh token."""
    return secrets.token_urlsafe(32)


# =============================================================================
# Metadata Endpoints (RFC 9728)
# =============================================================================


@router.get(
    "/.well-known/oauth-protected-resource",
    response_model=ProtectedResourceMetadata,
)
async def oauth_protected_resource_metadata() -> ProtectedResourceMetadata:
    """OAuth 2.0 Protected Resource Metadata per RFC 9728."""
    base_url = _get_base_url()

    return ProtectedResourceMetadata(
        resource=base_url,
        authorization_servers=[base_url],
        scopes_supported=SUPPORTED_SCOPES,
        bearer_methods_supported=["header"],
    )


@router.get(
    "/.well-known/oauth-authorization-server",
    response_model=OAuthMetadata,
)
async def oauth_authorization_server_metadata() -> OAuthMetadata:
    """OAuth 2.1 Authorization Server Metadata."""
    base_url = _get_base_url()

    return OAuthMetadata(
        issuer=base_url,
        authorization_endpoint=f"{base_url}/oauth/authorize",
        token_endpoint=f"{base_url}/oauth/token",
        registration_endpoint=f"{base_url}/oauth/register",
        scopes_supported=SUPPORTED_SCOPES,
        response_types_supported=["code"],
        grant_types_supported=["authorization_code", "refresh_token"],
        code_challenge_methods_supported=["S256"],
        token_endpoint_auth_methods_supported=["none", "client_secret_post"],
    )


# =============================================================================
# Dynamic Client Registration (RFC 7591)
# =============================================================================


@router.post("/oauth/register", response_model=ClientRegistrationResponse)
async def register_client(
    request: ClientRegistrationRequest,
) -> ClientRegistrationResponse:
    """Register a new OAuth client dynamically.

    ChatGPT Apps use DCR to register a fresh client per connection.
    """
    client_id = f"chatgpt_{secrets.token_urlsafe(16)}"
    client_secret = None
    client_secret_hash = None

    if request.token_endpoint_auth_method == "client_secret_post":
        client_secret = secrets.token_urlsafe(32)
        client_secret_hash = _hash_secret(client_secret)

    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(hours=CLIENT_REGISTRATION_LIFETIME_HOURS)

    client = OAuthClient(
        client_id=client_id,
        client_secret_hash=client_secret_hash,
        redirect_uris=request.redirect_uris,
        grant_types=request.grant_types,
        token_endpoint_auth_method=request.token_endpoint_auth_method,
        created_at=now,
        expires_at=expires_at,
    )
    _oauth_clients[client_id] = client

    logger.info(f"Registered OAuth client: {client_id}")

    return ClientRegistrationResponse(
        client_id=client_id,
        client_secret=client_secret,
        client_id_issued_at=int(now.timestamp()),
        client_secret_expires_at=int(expires_at.timestamp()),
        redirect_uris=request.redirect_uris,
        token_endpoint_auth_method=request.token_endpoint_auth_method,
        grant_types=request.grant_types,
        response_types=request.response_types,
    )


# =============================================================================
# Authorization Endpoint
# =============================================================================


@router.get("/oauth/authorize", response_model=None)
async def authorize(
    request: Request,
    client_id: Annotated[str, Query(description="Client identifier")],
    redirect_uri: Annotated[str, Query(description="Redirect URI")],
    response_type: Annotated[str, Query(description="Must be 'code'")] = "code",
    scope: Annotated[str, Query(description="Requested scopes")] = DEFAULT_SCOPE,
    state: Annotated[str, Query(description="CSRF state")] = "",
    code_challenge: Annotated[str, Query(description="PKCE challenge")] = "",
    code_challenge_method: Annotated[str, Query(description="PKCE method")] = "S256",
) -> HTMLResponse | RedirectResponse:
    """OAuth 2.1 Authorization Endpoint with PKCE."""
    if response_type != "code":
        return _authorization_error(
            redirect_uri, state, "unsupported_response_type",
            "Only 'code' response type is supported"
        )

    client = _oauth_clients.get(client_id)
    if not client:
        return _authorization_error(
            redirect_uri, state, "invalid_client",
            "Client not registered"
        )

    if client.expires_at and datetime.now(timezone.utc) > client.expires_at:
        del _oauth_clients[client_id]
        return _authorization_error(
            redirect_uri, state, "invalid_client",
            "Client registration expired"
        )

    if redirect_uri not in client.redirect_uris:
        return _authorization_error(
            redirect_uri, state, "invalid_request",
            "Redirect URI not registered"
        )

    if not code_challenge:
        return _authorization_error(
            redirect_uri, state, "invalid_request",
            "PKCE code_challenge is required"
        )

    if code_challenge_method != "S256":
        return _authorization_error(
            redirect_uri, state, "invalid_request",
            "Only S256 code_challenge_method is supported"
        )

    return HTMLResponse(content=_render_login_page(
        client_id=client_id,
        redirect_uri=redirect_uri,
        scope=scope,
        state=state,
        code_challenge=code_challenge,
        code_challenge_method=code_challenge_method,
    ))


@router.post("/oauth/authorize", response_model=None)
async def authorize_submit(
    request: Request,
    client_id: Annotated[str, Form()],
    redirect_uri: Annotated[str, Form()],
    scope: Annotated[str, Form()],
    state: Annotated[str, Form()],
    code_challenge: Annotated[str, Form()],
    code_challenge_method: Annotated[str, Form()],
    email: Annotated[str, Form()],
    action: Annotated[str, Form()],
) -> RedirectResponse:
    """Handle authorization form submission."""
    if action != "approve":
        return _authorization_error(
            redirect_uri, state, "access_denied",
            "User denied the authorization request"
        )

    client = _oauth_clients.get(client_id)
    if not client:
        return _authorization_error(
            redirect_uri, state, "invalid_client",
            "Client not found"
        )

    user_id = email
    learner_id = f"learner_{_hash_secret(email)[:12]}"

    code = secrets.token_urlsafe(32)
    code_hash = _hash_secret(code)

    auth_code = OAuthAuthCode(
        code_hash=code_hash,
        client_id=client_id,
        user_id=user_id,
        learner_id=learner_id,
        redirect_uri=redirect_uri,
        scope=scope,
        code_challenge=code_challenge,
        code_challenge_method=code_challenge_method,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=AUTH_CODE_LIFETIME_MINUTES),
    )
    _auth_codes[code_hash] = auth_code

    logger.info(f"Issued authorization code for user: {user_id}")

    params = {"code": code, "state": state}
    redirect_url = f"{redirect_uri}?{urlencode(params)}"
    return RedirectResponse(url=redirect_url, status_code=302)


def _authorization_error(
    redirect_uri: str,
    state: str,
    error: str,
    description: str,
) -> RedirectResponse:
    """Create an authorization error redirect."""
    params = {
        "error": error,
        "error_description": description,
        "state": state,
    }
    redirect_url = f"{redirect_uri}?{urlencode(params)}"
    return RedirectResponse(url=redirect_url, status_code=302)


def _render_login_page(
    client_id: str,
    redirect_uri: str,
    scope: str,
    state: str,
    code_challenge: str,
    code_challenge_method: str,
) -> str:
    """Render a simple login/consent page.

    In production, this would be a proper login page integrated
    with NextAuth or your existing authentication system.
    """
    scopes_display = scope.replace(":", " ").replace("_", " ").title()

    return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SAGE - Authorize ChatGPT</title>
    <style>
        body {{
            font-family: system-ui, -apple-system, sans-serif;
            max-width: 400px;
            margin: 50px auto;
            padding: 20px;
            background: #f5f5f5;
        }}
        .card {{
            background: white;
            border-radius: 8px;
            padding: 30px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #7c3aed;
            margin-bottom: 20px;
        }}
        .scopes {{
            background: #f0f0f0;
            padding: 15px;
            border-radius: 4px;
            margin: 20px 0;
        }}
        .scope {{
            display: flex;
            align-items: center;
            margin: 8px 0;
        }}
        .scope::before {{
            content: "✓";
            color: #10b981;
            margin-right: 10px;
        }}
        input[type="email"] {{
            width: 100%;
            padding: 12px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 16px;
            box-sizing: border-box;
        }}
        .buttons {{
            display: flex;
            gap: 10px;
            margin-top: 20px;
        }}
        button {{
            flex: 1;
            padding: 12px;
            border: none;
            border-radius: 4px;
            font-size: 16px;
            cursor: pointer;
        }}
        .approve {{
            background: #7c3aed;
            color: white;
        }}
        .deny {{
            background: #e5e5e5;
            color: #333;
        }}
    </style>
</head>
<body>
    <div class="card">
        <h1>SAGE</h1>
        <p>ChatGPT wants to access your SAGE account</p>

        <div class="scopes">
            <strong>Requested permissions:</strong>
            <div class="scope">Read your learning progress</div>
            <div class="scope">Update your learning data</div>
            <div class="scope">Manage learning sessions</div>
        </div>

        <form method="POST" action="/oauth/authorize">
            <input type="hidden" name="client_id" value="{client_id}">
            <input type="hidden" name="redirect_uri" value="{redirect_uri}">
            <input type="hidden" name="scope" value="{scope}">
            <input type="hidden" name="state" value="{state}">
            <input type="hidden" name="code_challenge" value="{code_challenge}">
            <input type="hidden" name="code_challenge_method" value="{code_challenge_method}">

            <label for="email">Your email:</label>
            <input type="email" id="email" name="email" required
                   placeholder="you@example.com">

            <div class="buttons">
                <button type="submit" name="action" value="deny" class="deny">
                    Deny
                </button>
                <button type="submit" name="action" value="approve" class="approve">
                    Authorize
                </button>
            </div>
        </form>
    </div>
</body>
</html>
"""


# =============================================================================
# Token Endpoint
# =============================================================================


@router.post("/oauth/token")
async def token(
    grant_type: Annotated[str, Form()],
    client_id: Annotated[str, Form()],
    client_secret: Annotated[str | None, Form()] = None,
    code: Annotated[str | None, Form()] = None,
    redirect_uri: Annotated[str | None, Form()] = None,
    code_verifier: Annotated[str | None, Form()] = None,
    refresh_token: Annotated[str | None, Form()] = None,
) -> TokenResponse | TokenErrorResponse:
    """OAuth 2.1 Token Endpoint."""
    client = _oauth_clients.get(client_id)
    if not client:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid client",
        )

    if client.token_endpoint_auth_method == "client_secret_post":
        if not client_secret or client.client_secret_hash != _hash_secret(client_secret):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid client credentials",
            )

    if grant_type == "authorization_code":
        return _handle_authorization_code_grant(
            client_id=client_id,
            code=code,
            redirect_uri=redirect_uri,
            code_verifier=code_verifier,
        )

    if grant_type == "refresh_token":
        return _handle_refresh_token_grant(
            client_id=client_id,
            refresh_token=refresh_token,
        )

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"Unsupported grant_type: {grant_type}",
    )


def _handle_authorization_code_grant(
    client_id: str,
    code: str | None,
    redirect_uri: str | None,
    code_verifier: str | None,
) -> TokenResponse:
    """Handle authorization_code grant type."""
    if not code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="code is required")
    if not redirect_uri:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="redirect_uri is required")
    if not code_verifier:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="code_verifier is required for PKCE")

    code_hash = _hash_secret(code)
    auth_code = _auth_codes.get(code_hash)

    if not auth_code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired authorization code")

    if datetime.now(timezone.utc) > auth_code.expires_at:
        del _auth_codes[code_hash]
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Authorization code expired")

    if auth_code.client_id != client_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Client ID mismatch")

    if auth_code.redirect_uri != redirect_uri:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Redirect URI mismatch")

    if not _verify_pkce(code_verifier, auth_code.code_challenge):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid code_verifier")

    del _auth_codes[code_hash]

    access_token = _generate_access_token(
        user_id=auth_code.user_id,
        learner_id=auth_code.learner_id,
        scope=auth_code.scope,
        client_id=client_id,
    )

    refresh_token_value = _generate_refresh_token()
    refresh_token_hash = _hash_secret(refresh_token_value)

    _refresh_tokens[refresh_token_hash] = OAuthRefreshToken(
        token_hash=refresh_token_hash,
        client_id=client_id,
        user_id=auth_code.user_id,
        learner_id=auth_code.learner_id,
        scope=auth_code.scope,
        expires_at=datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_LIFETIME_DAYS),
    )

    logger.info(f"Issued tokens for user: {auth_code.user_id}")

    return TokenResponse(
        access_token=access_token,
        token_type="Bearer",
        expires_in=ACCESS_TOKEN_LIFETIME_SECONDS,
        refresh_token=refresh_token_value,
        scope=auth_code.scope,
    )


def _handle_refresh_token_grant(
    client_id: str,
    refresh_token: str | None,
) -> TokenResponse:
    """Handle refresh_token grant type with token rotation."""
    if not refresh_token:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="refresh_token is required")

    token_hash = _hash_secret(refresh_token)
    stored_token = _refresh_tokens.get(token_hash)

    if not stored_token:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid refresh token")

    if stored_token.revoked_at:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Refresh token has been revoked")

    if stored_token.expires_at and datetime.now(timezone.utc) > stored_token.expires_at:
        del _refresh_tokens[token_hash]
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Refresh token expired")

    if stored_token.client_id != client_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Client ID mismatch")

    access_token = _generate_access_token(
        user_id=stored_token.user_id,
        learner_id=stored_token.learner_id,
        scope=stored_token.scope,
        client_id=client_id,
    )

    new_refresh_token = _generate_refresh_token()
    new_token_hash = _hash_secret(new_refresh_token)

    stored_token.revoked_at = datetime.now(timezone.utc)
    _refresh_tokens[new_token_hash] = OAuthRefreshToken(
        token_hash=new_token_hash,
        client_id=client_id,
        user_id=stored_token.user_id,
        learner_id=stored_token.learner_id,
        scope=stored_token.scope,
        expires_at=datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_LIFETIME_DAYS),
    )

    logger.info(f"Refreshed tokens for user: {stored_token.user_id}")

    return TokenResponse(
        access_token=access_token,
        token_type="Bearer",
        expires_in=ACCESS_TOKEN_LIFETIME_SECONDS,
        refresh_token=new_refresh_token,
        scope=stored_token.scope,
    )


# =============================================================================
# Token Revocation
# =============================================================================


@router.post("/oauth/revoke")
async def revoke_token(
    token: Annotated[str, Form()],
    token_type_hint: Annotated[str | None, Form()] = None,
    client_id: Annotated[str, Form()] = "",
) -> dict:
    """Revoke an access or refresh token.

    Per RFC 7009, this endpoint always returns 200 OK
    regardless of whether the token was actually revoked.
    """
    # Try to revoke as refresh token
    token_hash = _hash_secret(token)
    stored_token = _refresh_tokens.get(token_hash)

    if stored_token and not stored_token.revoked_at:
        # Verify client_id if provided
        if client_id and stored_token.client_id != client_id:
            pass  # Silently ignore - don't reveal token ownership
        else:
            stored_token.revoked_at = datetime.now(timezone.utc)
            logger.info(f"Revoked refresh token for user: {stored_token.user_id}")

    # Access tokens can't be revoked (they're short-lived JWTs)
    # Client should just discard them

    return {}
