"""
Authentication Endpoints
Handles user registration, login, token refresh
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from datetime import timedelta
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
import uuid
import logging

from core.database import get_db
from core.auth import (
    authenticate_user,
    create_access_token,
    create_refresh_token,
    get_password_hash,
    decode_token,
    get_current_user,
    get_current_admin_user,
    rate_limit_check,
    api_rate_limiter
)
from core.config import settings
from models.database import User, UserRole

logger = logging.getLogger(__name__)

router = APIRouter()
security = HTTPBearer()


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class UserRegisterRequest(BaseModel):
    """User registration request"""
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)
    full_name: str = Field(..., min_length=2, max_length=200)
    company: Optional[str] = None
    department: Optional[str] = None
    phone: Optional[str] = None


class UserLoginRequest(BaseModel):
    """User login request"""
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Token response"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class UserResponse(BaseModel):
    """User response"""
    id: str
    email: str
    full_name: str
    role: str
    is_active: bool
    is_admin: bool
    company: Optional[str]
    department: Optional[str]
    preferred_language: str
    preferred_jurisdiction: str


class RefreshTokenRequest(BaseModel):
    """Refresh token request"""
    refresh_token: str


# ============================================================================
# AUTHENTICATION ENDPOINTS
# ============================================================================

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    request: UserRegisterRequest,
    db: Session = Depends(get_db)
):
    """
    Register a new user

    - **email**: Valid email address (unique)
    - **password**: Password (min 8 characters)
    - **full_name**: User's full name
    - **company**: Optional company name
    - **department**: Optional department
    - **phone**: Optional phone number
    """
    # Rate limiting
    await rate_limit_check(request.email, api_rate_limiter)

    # Check if user already exists
    existing_user = db.query(User).filter(User.email == request.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Create new user
    user_id = str(uuid.uuid4())
    hashed_password = get_password_hash(request.password)

    new_user = User(
        id=user_id,
        email=request.email,
        hashed_password=hashed_password,
        full_name=request.full_name,
        company=request.company,
        department=request.department,
        phone=request.phone,
        role=UserRole.USER,
        is_active=True,
        is_admin=False
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    logger.info(f"New user registered: {user_id} ({request.email})")

    return UserResponse(**new_user.to_dict())


@router.post("/login", response_model=TokenResponse)
async def login(
    request: UserLoginRequest,
    db: Session = Depends(get_db)
):
    """
    Login with email and password

    Returns access token and refresh token
    """
    # Rate limiting
    await rate_limit_check(request.email, api_rate_limiter)

    # Authenticate user
    user = authenticate_user(db, request.email, request.password)
    if not user:
        logger.warning(f"Failed login attempt for: {request.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive"
        )

    # Create tokens
    access_token = create_access_token(
        data={"sub": user.id, "email": user.email, "role": user.role}
    )
    refresh_token = create_refresh_token(
        data={"sub": user.id, "email": user.email}
    )

    # Update last login
    from datetime import datetime
    user.last_login = datetime.utcnow()
    db.commit()

    logger.info(f"User logged in: {user.id} ({user.email})")

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    """
    Refresh access token using refresh token

    Returns new access token and refresh token
    """
    # Decode refresh token
    try:
        payload = decode_token(request.refresh_token)

        # Verify it's a refresh token
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )

        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )

        # Get user
        user = db.query(User).filter(User.id == user_id).first()
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )

        # Create new tokens
        access_token = create_access_token(
            data={"sub": user.id, "email": user.email, "role": user.role}
        )
        new_refresh_token = create_refresh_token(
            data={"sub": user.id, "email": user.email}
        )

        logger.info(f"Token refreshed for user: {user.id}")

        return TokenResponse(
            access_token=access_token,
            refresh_token=new_refresh_token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not refresh token"
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """
    Get current authenticated user information

    Requires: Bearer token in Authorization header
    """
    return UserResponse(**current_user.to_dict())


@router.put("/me", response_model=UserResponse)
async def update_current_user(
    full_name: Optional[str] = None,
    company: Optional[str] = None,
    department: Optional[str] = None,
    phone: Optional[str] = None,
    preferred_language: Optional[str] = None,
    preferred_jurisdiction: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update current user profile

    Requires: Bearer token in Authorization header
    """
    # Update fields if provided
    if full_name:
        current_user.full_name = full_name
    if company:
        current_user.company = company
    if department:
        current_user.department = department
    if phone:
        current_user.phone = phone
    if preferred_language in ["fr", "en"]:
        current_user.preferred_language = preferred_language
    if preferred_jurisdiction:
        current_user.preferred_jurisdiction = preferred_jurisdiction

    db.commit()
    db.refresh(current_user)

    logger.info(f"User profile updated: {current_user.id}")

    return UserResponse(**current_user.to_dict())


@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_user)
):
    """
    Logout current user

    Note: JWT tokens are stateless, so this is mainly for logging purposes.
    Client should discard the tokens.
    """
    logger.info(f"User logged out: {current_user.id}")

    return {
        "message": "Successfully logged out",
        "detail": "Please discard your access and refresh tokens"
    }


# ============================================================================
# ADMIN ENDPOINTS
# ============================================================================

@router.get("/users", dependencies=[Depends(get_current_admin_user)])
async def list_users(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """
    List all users (Admin only)

    Requires: Admin privileges
    """
    users = db.query(User).offset(skip).limit(limit).all()
    total = db.query(User).count()

    return {
        "users": [UserResponse(**user.to_dict()) for user in users],
        "total": total,
        "skip": skip,
        "limit": limit
    }


@router.put("/users/{user_id}/role", dependencies=[Depends(get_current_admin_user)])
async def update_user_role(
    user_id: str,
    role: UserRole,
    db: Session = Depends(get_db)
):
    """
    Update user role (Admin only)

    Requires: Admin privileges
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    user.role = role
    user.is_admin = (role == UserRole.ADMIN)
    db.commit()
    db.refresh(user)

    logger.info(f"User role updated: {user_id} -> {role}")

    return UserResponse(**user.to_dict())


@router.put("/users/{user_id}/status", dependencies=[Depends(get_current_admin_user)])
async def update_user_status(
    user_id: str,
    is_active: bool,
    db: Session = Depends(get_db)
):
    """
    Activate or deactivate user (Admin only)

    Requires: Admin privileges
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    user.is_active = is_active
    db.commit()
    db.refresh(user)

    logger.info(f"User status updated: {user_id} -> active={is_active}")

    return UserResponse(**user.to_dict())


@router.delete("/users/{user_id}", dependencies=[Depends(get_current_admin_user)])
async def delete_user(
    user_id: str,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Delete user (Admin only)

    Requires: Admin privileges
    Note: Cannot delete yourself
    """
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete yourself"
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    db.delete(user)
    db.commit()

    logger.info(f"User deleted: {user_id}")

    return {"message": "User deleted successfully"}
