from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.schemas.user import LoginRequest, Token, UserCreate, UserOut
from app.services.auth_service import authenticate_user, register_user
from app.utils.security import create_access_token

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
def register(payload: UserCreate, db: Session = Depends(get_db)) -> UserOut:
    """Create a new user account. Public endpoint."""
    user = register_user(db, payload)
    return user


@router.post(
    "/login",
    response_model=Token,
    summary="Log in and receive a JWT access token",
)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> Token:
    """Authenticate with username + password. Returns a bearer token. Public endpoint."""
    user = authenticate_user(db, payload.username, payload.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": str(user.id)})
    return Token(access_token=access_token, token_type="bearer")
from app.dependencies import get_current_user
from app.models.user import User
from fastapi import Depends

@router.get("/me")
def get_me(user: User = Depends(get_current_user)):
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email
    }