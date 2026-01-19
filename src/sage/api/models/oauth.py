"""OAuth 2.1 Pydantic models for ChatGPT App authentication.

Implements RFC 9728 (Protected Resource Metadata), RFC 7591 (DCR),
and OAuth 2.1 with PKCE support.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


# =============================================================================
# Metadata Models (RFC 9728)
# =============================================================================


class ProtectedResourceMetadata(BaseModel):
    """OAuth 2.0 Protected Resource Metadata per RFC 9728."""

    resource: str = Field(description="Resource identifier URL")
    authorization_servers: list[str] = Field(
        description="List of authorization server URLs"
    )
    scopes_supported: list[str] = Field(
        default_factory=list,
        description="Supported OAuth scopes",
    )
    bearer_methods_supported: list[str] = Field(
        default=["header"],
        description="Token delivery methods",
    )


class OAuthMetadata(BaseModel):
    """OAuth 2.1 Authorization Server Metadata."""

    issuer: str = Field(description="Authorization server issuer URL")
    authorization_endpoint: str = Field(description="Authorization endpoint URL")
    token_endpoint: str = Field(description="Token endpoint URL")
    registration_endpoint: str | None = Field(
        default=None,
        description="Dynamic client registration endpoint",
    )
    scopes_supported: list[str] = Field(
        default_factory=list,
        description="Supported scopes",
    )
    response_types_supported: list[str] = Field(
        default=["code"],
        description="Supported response types",
    )
    grant_types_supported: list[str] = Field(
        default=["authorization_code", "refresh_token"],
        description="Supported grant types",
    )
    code_challenge_methods_supported: list[str] = Field(
        default=["S256"],
        description="PKCE code challenge methods",
    )
    token_endpoint_auth_methods_supported: list[str] = Field(
        default=["none", "client_secret_post"],
        description="Token endpoint auth methods",
    )


# =============================================================================
# Dynamic Client Registration (RFC 7591)
# =============================================================================


class ClientRegistrationRequest(BaseModel):
    """OAuth 2.0 Dynamic Client Registration Request per RFC 7591."""

    redirect_uris: list[str] = Field(
        description="List of allowed redirect URIs"
    )
    client_name: str | None = Field(
        default=None,
        description="Human-readable client name",
    )
    token_endpoint_auth_method: str = Field(
        default="none",
        description="Authentication method for token endpoint",
    )
    grant_types: list[str] = Field(
        default=["authorization_code", "refresh_token"],
        description="Requested grant types",
    )
    response_types: list[str] = Field(
        default=["code"],
        description="Requested response types",
    )
    scope: str | None = Field(
        default=None,
        description="Space-separated list of requested scopes",
    )


class ClientRegistrationResponse(BaseModel):
    """OAuth 2.0 Dynamic Client Registration Response."""

    client_id: str = Field(description="Unique client identifier")
    client_secret: str | None = Field(
        default=None,
        description="Client secret (only for confidential clients)",
    )
    client_id_issued_at: int = Field(
        description="Unix timestamp when client_id was issued"
    )
    client_secret_expires_at: int = Field(
        default=0,
        description="Unix timestamp when secret expires (0 = never)",
    )
    redirect_uris: list[str] = Field(description="Registered redirect URIs")
    token_endpoint_auth_method: str = Field(
        description="Token endpoint auth method"
    )
    grant_types: list[str] = Field(description="Allowed grant types")
    response_types: list[str] = Field(description="Allowed response types")


# =============================================================================
# Authorization Request/Response
# =============================================================================


class AuthorizationRequest(BaseModel):
    """OAuth 2.1 Authorization Request with PKCE."""

    client_id: str = Field(description="Client identifier")
    redirect_uri: str = Field(description="Redirect URI after authorization")
    response_type: Literal["code"] = Field(
        default="code",
        description="Must be 'code' for authorization code flow",
    )
    scope: str = Field(
        default="learner:read learner:write session:manage",
        description="Space-separated list of scopes",
    )
    state: str = Field(description="CSRF protection state parameter")
    code_challenge: str = Field(description="PKCE code challenge")
    code_challenge_method: Literal["S256"] = Field(
        default="S256",
        description="PKCE code challenge method (must be S256)",
    )


# =============================================================================
# Token Request/Response
# =============================================================================


class TokenRequest(BaseModel):
    """OAuth 2.1 Token Request."""

    grant_type: Literal["authorization_code", "refresh_token"] = Field(
        description="Grant type"
    )
    client_id: str = Field(description="Client identifier")
    client_secret: str | None = Field(
        default=None,
        description="Client secret (if applicable)",
    )

    # For authorization_code grant
    code: str | None = Field(
        default=None,
        description="Authorization code (required for authorization_code grant)",
    )
    redirect_uri: str | None = Field(
        default=None,
        description="Redirect URI (required for authorization_code grant)",
    )
    code_verifier: str | None = Field(
        default=None,
        description="PKCE code verifier (required for authorization_code grant)",
    )

    # For refresh_token grant
    refresh_token: str | None = Field(
        default=None,
        description="Refresh token (required for refresh_token grant)",
    )


class TokenResponse(BaseModel):
    """OAuth 2.1 Token Response."""

    access_token: str = Field(description="JWT access token")
    token_type: Literal["Bearer"] = Field(
        default="Bearer",
        description="Token type",
    )
    expires_in: int = Field(
        default=3600,
        description="Token lifetime in seconds",
    )
    refresh_token: str | None = Field(
        default=None,
        description="Refresh token for obtaining new access tokens",
    )
    scope: str = Field(description="Granted scopes")


class TokenErrorResponse(BaseModel):
    """OAuth 2.1 Token Error Response."""

    error: str = Field(description="Error code")
    error_description: str | None = Field(
        default=None,
        description="Human-readable error description",
    )


# =============================================================================
# Database Models
# =============================================================================


class OAuthClient(BaseModel):
    """Registered OAuth client stored in database."""

    client_id: str = Field(description="Unique client identifier")
    client_secret_hash: str | None = Field(
        default=None,
        description="Hashed client secret",
    )
    redirect_uris: list[str] = Field(description="Allowed redirect URIs")
    grant_types: list[str] = Field(description="Allowed grant types")
    token_endpoint_auth_method: str = Field(
        default="none",
        description="Token endpoint auth method",
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When client was registered",
    )
    expires_at: datetime | None = Field(
        default=None,
        description="When registration expires (None = never)",
    )


class OAuthAuthCode(BaseModel):
    """Authorization code stored in database."""

    code_hash: str = Field(description="Hashed authorization code")
    client_id: str = Field(description="Client that requested the code")
    user_id: str = Field(description="User who authorized")
    learner_id: str = Field(description="Associated learner ID")
    redirect_uri: str = Field(description="Redirect URI for this code")
    scope: str = Field(description="Granted scopes")
    code_challenge: str = Field(description="PKCE code challenge")
    code_challenge_method: str = Field(
        default="S256",
        description="PKCE method",
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When code was created",
    )
    expires_at: datetime = Field(description="When code expires")


class OAuthRefreshToken(BaseModel):
    """Refresh token stored in database."""

    token_hash: str = Field(description="Hashed refresh token")
    client_id: str = Field(description="Client that owns the token")
    user_id: str = Field(description="User who authorized")
    learner_id: str = Field(description="Associated learner ID")
    scope: str = Field(description="Granted scopes")
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When token was created",
    )
    expires_at: datetime | None = Field(
        default=None,
        description="When token expires (None = never)",
    )
    revoked_at: datetime | None = Field(
        default=None,
        description="When token was revoked",
    )
