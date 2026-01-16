"""Authentication routes for SAGE."""

import hashlib
import secrets
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr

from sage.graph.learning_graph import LearningGraph
from sage.graph.models import Learner, LearnerProfile

from ..deps import get_graph

router = APIRouter(prefix="/api/auth", tags=["auth"])


# =============================================================================
# Request/Response Models
# =============================================================================


class LoginRequest(BaseModel):
    """Login with email and password."""

    email: EmailStr
    password: str


class RegisterRequest(BaseModel):
    """Register a new user."""

    email: EmailStr
    password: str
    name: str


class SyncRequest(BaseModel):
    """Sync OAuth user with backend."""

    provider_id: str
    provider: str
    email: Optional[str] = None
    name: Optional[str] = None


class AuthResponse(BaseModel):
    """Authentication response with user details."""

    id: str
    email: str
    name: str
    learner_id: str


# =============================================================================
# Password Utilities
# =============================================================================


def _hash_password(password: str, salt: Optional[str] = None) -> tuple[str, str]:
    """Hash password with salt using PBKDF2.

    Args:
        password: Plain text password
        salt: Optional salt (generated if not provided)

    Returns:
        Tuple of (hash, salt)
    """
    if salt is None:
        salt = secrets.token_hex(16)
    hashed = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode(),
        salt.encode(),
        100000,
    )
    return hashed.hex(), salt


def _verify_password(password: str, password_hash: str, salt: str) -> bool:
    """Verify a password against its hash."""
    computed_hash, _ = _hash_password(password, salt)
    return secrets.compare_digest(computed_hash, password_hash)


# =============================================================================
# Routes
# =============================================================================


@router.post("/register", response_model=AuthResponse)
async def register(
    data: RegisterRequest,
    graph: LearningGraph = Depends(get_graph),
) -> AuthResponse:
    """Register a new user with email/password.

    Creates a new learner profile and links it to the user account.
    """
    # Check if email already exists
    existing = graph.get_user_by_email(data.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Create learner first
    learner = Learner(profile=LearnerProfile(name=data.name))
    graph.create_learner(learner)

    # Hash password
    password_hash, password_salt = _hash_password(data.password)

    # Create user
    user_id = secrets.token_urlsafe(16)
    graph.create_user(
        user_id=user_id,
        learner_id=learner.id,
        email=data.email,
        name=data.name,
        provider="credentials",
        password_hash=password_hash,
        password_salt=password_salt,
    )

    return AuthResponse(
        id=user_id,
        email=data.email,
        name=data.name,
        learner_id=learner.id,
    )


@router.post("/login", response_model=AuthResponse)
async def login(
    data: LoginRequest,
    graph: LearningGraph = Depends(get_graph),
) -> AuthResponse:
    """Login with email/password."""
    user = graph.get_user_by_email(data.email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    # Verify password
    if not user.get("password_hash") or not user.get("password_salt"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    if not _verify_password(data.password, user["password_hash"], user["password_salt"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    # Update last login
    graph.update_user_last_login(user["id"])

    return AuthResponse(
        id=user["id"],
        email=user["email"] or "",
        name=user["name"] or "",
        learner_id=user["learner_id"],
    )


@router.post("/sync", response_model=AuthResponse)
async def sync_oauth(
    data: SyncRequest,
    graph: LearningGraph = Depends(get_graph),
) -> AuthResponse:
    """Sync OAuth user with backend, creating learner if needed.

    Called by NextAuth.js after OAuth login to ensure user exists in backend.
    """
    # Check if user exists by provider ID
    user = graph.get_user(data.provider_id)

    if user:
        # Existing user - update last login
        graph.update_user_last_login(user["id"])
        return AuthResponse(
            id=user["id"],
            email=user.get("email") or "",
            name=user.get("name") or "",
            learner_id=user["learner_id"],
        )

    # Check if email already has an account (different provider)
    if data.email:
        existing = graph.get_user_by_email(data.email)
        if existing:
            # Link to existing learner
            graph.create_user(
                user_id=data.provider_id,
                learner_id=existing["learner_id"],
                email=data.email,
                name=data.name,
                provider=data.provider,
            )
            return AuthResponse(
                id=data.provider_id,
                email=data.email,
                name=data.name or "",
                learner_id=existing["learner_id"],
            )

    # New OAuth user - create learner and user
    learner = Learner(profile=LearnerProfile(name=data.name))
    graph.create_learner(learner)

    graph.create_user(
        user_id=data.provider_id,
        learner_id=learner.id,
        email=data.email,
        name=data.name,
        provider=data.provider,
    )

    return AuthResponse(
        id=data.provider_id,
        email=data.email or "",
        name=data.name or "",
        learner_id=learner.id,
    )


@router.get("/me", response_model=AuthResponse)
async def get_current_user_info(
    graph: LearningGraph = Depends(get_graph),
    user_id: Optional[str] = None,  # Will be injected by auth middleware later
) -> AuthResponse:
    """Get current user info.

    NOTE: This endpoint requires authentication (to be added in Step 4).
    For now it returns a placeholder to test the route structure.
    """
    # This will be replaced with proper auth in Step 4
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    user = graph.get_user(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return AuthResponse(
        id=user["id"],
        email=user.get("email") or "",
        name=user.get("name") or "",
        learner_id=user["learner_id"],
    )
