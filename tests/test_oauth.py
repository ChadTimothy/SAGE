"""Tests for OAuth 2.1 authentication endpoints.

Tests cover:
- Protected Resource Metadata (RFC 9728)
- Authorization Server Metadata
- Dynamic Client Registration (RFC 7591)
- Authorization flow with PKCE
- Token exchange
- Token refresh with rotation
- Token revocation
- MCP token validation
"""

import base64
import hashlib
import secrets
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from jose import jwt

from sage.api.main import app
from sage.api.deps import get_graph
from sage.api.auth import jwt_bearer, jwt_bearer_optional
from sage.api.routes.oauth import (
    _oauth_clients,
    _auth_codes,
    _refresh_tokens,
    SUPPORTED_SCOPES,
    DEFAULT_SCOPE,
)
from sage.core.config import get_settings


# Test constants
TEST_SECRET = "test-secret-key-for-testing-only"
TEST_REDIRECT_URI = "https://chatgpt.com/callback"


def _generate_pkce_pair():
    """Generate a PKCE code_verifier and code_challenge pair."""
    code_verifier = secrets.token_urlsafe(32)
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    code_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return code_verifier, code_challenge


@pytest.fixture
def oauth_client(test_graph, mock_settings):
    """Create test client for OAuth endpoints."""
    def override_get_graph():
        yield test_graph

    app.dependency_overrides[get_graph] = override_get_graph

    # Clear OAuth state before each test
    _oauth_clients.clear()
    _auth_codes.clear()
    _refresh_tokens.clear()

    # Reset JWT bearer singletons to pick up mock settings
    jwt_bearer._settings = None
    jwt_bearer_optional._settings = None

    yield TestClient(app)

    app.dependency_overrides.clear()
    _oauth_clients.clear()
    _auth_codes.clear()
    _refresh_tokens.clear()
    jwt_bearer._settings = None
    jwt_bearer_optional._settings = None


@pytest.fixture
def registered_client(oauth_client):
    """Register an OAuth client and return its credentials."""
    response = oauth_client.post(
        "/oauth/register",
        json={
            "redirect_uris": [TEST_REDIRECT_URI],
            "client_name": "Test ChatGPT Client",
            "token_endpoint_auth_method": "none",
            "grant_types": ["authorization_code", "refresh_token"],
            "response_types": ["code"],
        },
    )
    assert response.status_code == 200
    return response.json()


class TestOAuthMetadata:
    """Tests for OAuth discovery/metadata endpoints."""

    def test_protected_resource_metadata(self, oauth_client):
        """Test /.well-known/oauth-protected-resource returns valid metadata."""
        response = oauth_client.get("/.well-known/oauth-protected-resource")

        assert response.status_code == 200
        data = response.json()

        assert "resource" in data
        assert "authorization_servers" in data
        assert len(data["authorization_servers"]) > 0
        assert "scopes_supported" in data
        assert set(SUPPORTED_SCOPES).issubset(set(data["scopes_supported"]))
        assert "bearer_methods_supported" in data
        assert "header" in data["bearer_methods_supported"]

    def test_authorization_server_metadata(self, oauth_client):
        """Test /.well-known/oauth-authorization-server returns valid metadata."""
        response = oauth_client.get("/.well-known/oauth-authorization-server")

        assert response.status_code == 200
        data = response.json()

        # Required OAuth 2.1 metadata fields
        assert "issuer" in data
        assert "authorization_endpoint" in data
        assert "token_endpoint" in data
        assert "registration_endpoint" in data

        # Verify endpoints contain expected paths
        assert "/oauth/authorize" in data["authorization_endpoint"]
        assert "/oauth/token" in data["token_endpoint"]
        assert "/oauth/register" in data["registration_endpoint"]

        # PKCE support (required for OAuth 2.1)
        assert "code_challenge_methods_supported" in data
        assert "S256" in data["code_challenge_methods_supported"]

        # Supported grant types
        assert "grant_types_supported" in data
        assert "authorization_code" in data["grant_types_supported"]
        assert "refresh_token" in data["grant_types_supported"]


class TestDynamicClientRegistration:
    """Tests for Dynamic Client Registration (RFC 7591)."""

    def test_register_client_success(self, oauth_client):
        """Test successful client registration."""
        response = oauth_client.post(
            "/oauth/register",
            json={
                "redirect_uris": [TEST_REDIRECT_URI],
                "client_name": "Test Client",
                "token_endpoint_auth_method": "none",
                "grant_types": ["authorization_code", "refresh_token"],
                "response_types": ["code"],
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert "client_id" in data
        assert data["client_id"].startswith("chatgpt_")
        assert "client_id_issued_at" in data
        assert "redirect_uris" in data
        assert TEST_REDIRECT_URI in data["redirect_uris"]
        assert data["token_endpoint_auth_method"] == "none"
        # No client_secret for public clients
        assert data.get("client_secret") is None

    def test_register_confidential_client(self, oauth_client):
        """Test registration with client_secret_post auth method."""
        response = oauth_client.post(
            "/oauth/register",
            json={
                "redirect_uris": [TEST_REDIRECT_URI],
                "token_endpoint_auth_method": "client_secret_post",
                "grant_types": ["authorization_code"],
                "response_types": ["code"],
            },
        )

        assert response.status_code == 200
        data = response.json()

        # Confidential clients get a secret
        assert "client_secret" in data
        assert data["client_secret"] is not None
        assert len(data["client_secret"]) > 20

    def test_client_stored_in_registry(self, oauth_client):
        """Test that registered client is stored."""
        response = oauth_client.post(
            "/oauth/register",
            json={
                "redirect_uris": [TEST_REDIRECT_URI],
            },
        )

        client_id = response.json()["client_id"]
        assert client_id in _oauth_clients


class TestAuthorizationEndpoint:
    """Tests for OAuth authorization endpoint."""

    def test_authorize_shows_login_page(self, oauth_client, registered_client):
        """Test authorization endpoint shows login page."""
        _, code_challenge = _generate_pkce_pair()

        response = oauth_client.get(
            "/oauth/authorize",
            params={
                "client_id": registered_client["client_id"],
                "redirect_uri": TEST_REDIRECT_URI,
                "response_type": "code",
                "scope": DEFAULT_SCOPE,
                "state": "test-state-123",
                "code_challenge": code_challenge,
                "code_challenge_method": "S256",
            },
            follow_redirects=False,
        )

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        # Check login form elements
        content = response.text
        assert "SAGE" in content
        assert "email" in content
        assert "Authorize" in content

    def test_authorize_invalid_client(self, oauth_client):
        """Test authorization with invalid client_id."""
        _, code_challenge = _generate_pkce_pair()

        response = oauth_client.get(
            "/oauth/authorize",
            params={
                "client_id": "invalid_client",
                "redirect_uri": TEST_REDIRECT_URI,
                "response_type": "code",
                "state": "test-state",
                "code_challenge": code_challenge,
                "code_challenge_method": "S256",
            },
            follow_redirects=False,
        )

        # Should redirect with error
        assert response.status_code == 302
        assert "error=invalid_client" in response.headers["location"]

    def test_authorize_invalid_redirect_uri(self, oauth_client, registered_client):
        """Test authorization with unregistered redirect_uri."""
        _, code_challenge = _generate_pkce_pair()

        response = oauth_client.get(
            "/oauth/authorize",
            params={
                "client_id": registered_client["client_id"],
                "redirect_uri": "https://evil.com/callback",
                "response_type": "code",
                "state": "test-state",
                "code_challenge": code_challenge,
                "code_challenge_method": "S256",
            },
            follow_redirects=False,
        )

        assert response.status_code == 302
        assert "error=invalid_request" in response.headers["location"]

    def test_authorize_missing_pkce(self, oauth_client, registered_client):
        """Test authorization without PKCE code_challenge fails."""
        response = oauth_client.get(
            "/oauth/authorize",
            params={
                "client_id": registered_client["client_id"],
                "redirect_uri": TEST_REDIRECT_URI,
                "response_type": "code",
                "state": "test-state",
                # No code_challenge
            },
            follow_redirects=False,
        )

        assert response.status_code == 302
        assert "error=invalid_request" in response.headers["location"]
        assert "code_challenge" in response.headers["location"]

    def test_authorize_submit_approve(self, oauth_client, registered_client):
        """Test approving authorization returns code."""
        code_verifier, code_challenge = _generate_pkce_pair()

        response = oauth_client.post(
            "/oauth/authorize",
            data={
                "client_id": registered_client["client_id"],
                "redirect_uri": TEST_REDIRECT_URI,
                "scope": DEFAULT_SCOPE,
                "state": "test-state-456",
                "code_challenge": code_challenge,
                "code_challenge_method": "S256",
                "email": "user@example.com",
                "action": "approve",
            },
            follow_redirects=False,
        )

        assert response.status_code == 302
        location = response.headers["location"]
        assert TEST_REDIRECT_URI in location
        assert "code=" in location
        assert "state=test-state-456" in location
        assert "error" not in location

    def test_authorize_submit_deny(self, oauth_client, registered_client):
        """Test denying authorization returns error."""
        _, code_challenge = _generate_pkce_pair()

        response = oauth_client.post(
            "/oauth/authorize",
            data={
                "client_id": registered_client["client_id"],
                "redirect_uri": TEST_REDIRECT_URI,
                "scope": DEFAULT_SCOPE,
                "state": "test-state",
                "code_challenge": code_challenge,
                "code_challenge_method": "S256",
                "email": "user@example.com",
                "action": "deny",
            },
            follow_redirects=False,
        )

        assert response.status_code == 302
        assert "error=access_denied" in response.headers["location"]


class TestTokenEndpoint:
    """Tests for OAuth token endpoint."""

    def _get_auth_code(self, oauth_client, registered_client):
        """Helper to get an authorization code."""
        code_verifier, code_challenge = _generate_pkce_pair()

        response = oauth_client.post(
            "/oauth/authorize",
            data={
                "client_id": registered_client["client_id"],
                "redirect_uri": TEST_REDIRECT_URI,
                "scope": DEFAULT_SCOPE,
                "state": "test-state",
                "code_challenge": code_challenge,
                "code_challenge_method": "S256",
                "email": "token@example.com",
                "action": "approve",
            },
            follow_redirects=False,
        )

        # Extract code from redirect
        location = response.headers["location"]
        code = location.split("code=")[1].split("&")[0]
        return code, code_verifier

    def test_token_exchange_success(self, oauth_client, registered_client):
        """Test exchanging auth code for tokens."""
        code, code_verifier = self._get_auth_code(oauth_client, registered_client)

        response = oauth_client.post(
            "/oauth/token",
            data={
                "grant_type": "authorization_code",
                "client_id": registered_client["client_id"],
                "code": code,
                "redirect_uri": TEST_REDIRECT_URI,
                "code_verifier": code_verifier,
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert "access_token" in data
        assert data["token_type"] == "Bearer"
        assert "expires_in" in data
        assert data["expires_in"] > 0
        assert "refresh_token" in data
        assert "scope" in data

    def test_token_is_valid_jwt(self, oauth_client, registered_client):
        """Test that access token is a valid JWT with correct claims."""
        code, code_verifier = self._get_auth_code(oauth_client, registered_client)

        response = oauth_client.post(
            "/oauth/token",
            data={
                "grant_type": "authorization_code",
                "client_id": registered_client["client_id"],
                "code": code,
                "redirect_uri": TEST_REDIRECT_URI,
                "code_verifier": code_verifier,
            },
        )

        access_token = response.json()["access_token"]

        # Decode without verification to check structure
        payload = jwt.get_unverified_claims(access_token)

        assert "sub" in payload  # User ID
        assert "learner_id" in payload  # SAGE learner ID
        assert "scope" in payload
        assert payload["source"] == "chatgpt"
        assert "iat" in payload
        assert "exp" in payload
        assert payload["exp"] > payload["iat"]

    def test_token_invalid_code(self, oauth_client, registered_client):
        """Test token request with invalid auth code."""
        response = oauth_client.post(
            "/oauth/token",
            data={
                "grant_type": "authorization_code",
                "client_id": registered_client["client_id"],
                "code": "invalid-code",
                "redirect_uri": TEST_REDIRECT_URI,
                "code_verifier": "some-verifier",
            },
        )

        assert response.status_code == 400
        assert "Invalid" in response.json()["detail"]

    def test_token_invalid_pkce_verifier(self, oauth_client, registered_client):
        """Test token request with wrong PKCE verifier."""
        code, _ = self._get_auth_code(oauth_client, registered_client)

        response = oauth_client.post(
            "/oauth/token",
            data={
                "grant_type": "authorization_code",
                "client_id": registered_client["client_id"],
                "code": code,
                "redirect_uri": TEST_REDIRECT_URI,
                "code_verifier": "wrong-verifier",  # Invalid
            },
        )

        assert response.status_code == 400
        assert "code_verifier" in response.json()["detail"]

    def test_token_code_single_use(self, oauth_client, registered_client):
        """Test that auth codes can only be used once."""
        code, code_verifier = self._get_auth_code(oauth_client, registered_client)

        # First use succeeds
        response1 = oauth_client.post(
            "/oauth/token",
            data={
                "grant_type": "authorization_code",
                "client_id": registered_client["client_id"],
                "code": code,
                "redirect_uri": TEST_REDIRECT_URI,
                "code_verifier": code_verifier,
            },
        )
        assert response1.status_code == 200

        # Second use fails
        response2 = oauth_client.post(
            "/oauth/token",
            data={
                "grant_type": "authorization_code",
                "client_id": registered_client["client_id"],
                "code": code,
                "redirect_uri": TEST_REDIRECT_URI,
                "code_verifier": code_verifier,
            },
        )
        assert response2.status_code == 400


class TestTokenRefresh:
    """Tests for refresh token grant."""

    def _get_tokens(self, oauth_client, registered_client):
        """Helper to get access and refresh tokens."""
        code_verifier, code_challenge = _generate_pkce_pair()

        # Get auth code
        auth_response = oauth_client.post(
            "/oauth/authorize",
            data={
                "client_id": registered_client["client_id"],
                "redirect_uri": TEST_REDIRECT_URI,
                "scope": DEFAULT_SCOPE,
                "state": "test",
                "code_challenge": code_challenge,
                "code_challenge_method": "S256",
                "email": "refresh@example.com",
                "action": "approve",
            },
            follow_redirects=False,
        )
        code = auth_response.headers["location"].split("code=")[1].split("&")[0]

        # Exchange for tokens
        token_response = oauth_client.post(
            "/oauth/token",
            data={
                "grant_type": "authorization_code",
                "client_id": registered_client["client_id"],
                "code": code,
                "redirect_uri": TEST_REDIRECT_URI,
                "code_verifier": code_verifier,
            },
        )
        return token_response.json()

    def test_refresh_token_success(self, oauth_client, registered_client):
        """Test refreshing access token."""
        tokens = self._get_tokens(oauth_client, registered_client)

        response = oauth_client.post(
            "/oauth/token",
            data={
                "grant_type": "refresh_token",
                "client_id": registered_client["client_id"],
                "refresh_token": tokens["refresh_token"],
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert "access_token" in data
        assert data["access_token"]  # Valid token returned
        assert "refresh_token" in data
        assert data["refresh_token"] != tokens["refresh_token"]  # Rotated

    def test_refresh_token_rotation(self, oauth_client, registered_client):
        """Test that refresh tokens are rotated (old one invalidated)."""
        tokens = self._get_tokens(oauth_client, registered_client)
        old_refresh = tokens["refresh_token"]

        # Refresh once
        response1 = oauth_client.post(
            "/oauth/token",
            data={
                "grant_type": "refresh_token",
                "client_id": registered_client["client_id"],
                "refresh_token": old_refresh,
            },
        )
        assert response1.status_code == 200

        # Try to use old refresh token again
        response2 = oauth_client.post(
            "/oauth/token",
            data={
                "grant_type": "refresh_token",
                "client_id": registered_client["client_id"],
                "refresh_token": old_refresh,
            },
        )
        assert response2.status_code == 400
        assert "revoked" in response2.json()["detail"]

    def test_refresh_invalid_token(self, oauth_client, registered_client):
        """Test refresh with invalid token."""
        response = oauth_client.post(
            "/oauth/token",
            data={
                "grant_type": "refresh_token",
                "client_id": registered_client["client_id"],
                "refresh_token": "invalid-refresh-token",
            },
        )

        assert response.status_code == 400
        assert "Invalid" in response.json()["detail"]


class TestTokenRevocation:
    """Tests for token revocation endpoint."""

    def test_revoke_refresh_token(self, oauth_client, registered_client):
        """Test revoking a refresh token."""
        # Get tokens first
        code_verifier, code_challenge = _generate_pkce_pair()

        auth_response = oauth_client.post(
            "/oauth/authorize",
            data={
                "client_id": registered_client["client_id"],
                "redirect_uri": TEST_REDIRECT_URI,
                "scope": DEFAULT_SCOPE,
                "state": "test",
                "code_challenge": code_challenge,
                "code_challenge_method": "S256",
                "email": "revoke@example.com",
                "action": "approve",
            },
            follow_redirects=False,
        )
        code = auth_response.headers["location"].split("code=")[1].split("&")[0]

        token_response = oauth_client.post(
            "/oauth/token",
            data={
                "grant_type": "authorization_code",
                "client_id": registered_client["client_id"],
                "code": code,
                "redirect_uri": TEST_REDIRECT_URI,
                "code_verifier": code_verifier,
            },
        )
        refresh_token = token_response.json()["refresh_token"]

        # Revoke it
        revoke_response = oauth_client.post(
            "/oauth/revoke",
            data={
                "token": refresh_token,
                "client_id": registered_client["client_id"],
            },
        )
        assert revoke_response.status_code == 200

        # Try to use it
        use_response = oauth_client.post(
            "/oauth/token",
            data={
                "grant_type": "refresh_token",
                "client_id": registered_client["client_id"],
                "refresh_token": refresh_token,
            },
        )
        assert use_response.status_code == 400

    def test_revoke_always_returns_200(self, oauth_client, registered_client):
        """Test that revocation always returns 200 (per RFC 7009)."""
        response = oauth_client.post(
            "/oauth/revoke",
            data={
                "token": "non-existent-token",
                "client_id": registered_client["client_id"],
            },
        )
        # Per RFC 7009, always return 200 regardless of token validity
        assert response.status_code == 200


class TestMCPTokenValidation:
    """Tests for OAuth token validation in API requests."""

    def _get_access_token(self, oauth_client, registered_client):
        """Helper to get an access token."""
        code_verifier, code_challenge = _generate_pkce_pair()

        auth_response = oauth_client.post(
            "/oauth/authorize",
            data={
                "client_id": registered_client["client_id"],
                "redirect_uri": TEST_REDIRECT_URI,
                "scope": DEFAULT_SCOPE,
                "state": "test",
                "code_challenge": code_challenge,
                "code_challenge_method": "S256",
                "email": "api@example.com",
                "action": "approve",
            },
            follow_redirects=False,
        )
        code = auth_response.headers["location"].split("code=")[1].split("&")[0]

        token_response = oauth_client.post(
            "/oauth/token",
            data={
                "grant_type": "authorization_code",
                "client_id": registered_client["client_id"],
                "code": code,
                "redirect_uri": TEST_REDIRECT_URI,
                "code_verifier": code_verifier,
            },
        )
        return token_response.json()["access_token"]

    def test_oauth_token_accepted_in_api(self, oauth_client, registered_client, test_graph):
        """Test that OAuth tokens are accepted by protected API endpoints."""
        access_token = self._get_access_token(oauth_client, registered_client)

        # Try to access a protected endpoint
        # Note: This will likely fail with 404 because learner doesn't exist,
        # but we're testing that auth passes (not 401)
        response = oauth_client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Should not be 401 Unauthorized (auth passed)
        # May be 404 if user doesn't exist, but auth worked
        assert response.status_code != 401

    def test_invalid_oauth_token_rejected(self, oauth_client):
        """Test that invalid OAuth tokens are rejected."""
        response = oauth_client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer invalid.jwt.token"},
        )

        assert response.status_code == 401
