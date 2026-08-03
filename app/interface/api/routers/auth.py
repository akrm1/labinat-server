"""Authentication: login, token refresh, logout, and current-user lookup."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.interface.api import schemas
from app.interface.api.deps import get_current_user
from app.interface.serializers import user_to_dict
from app.core.auth.User import User, InvalidCredentialsError
from app.core.auth.Session import Session
from app.base.Tokenizer import TokenError

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=schemas.TokenResponse)
def login(body: schemas.LoginRequest):
    try:
        session = User.authenticate(body.username, body.password)
    except InvalidCredentialsError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )
    return session.astokens()


@router.post("/refresh", response_model=schemas.TokenResponse)
def refresh(body: schemas.RefreshRequest):
    try:
        session = Session.refresh(body.refresh_token)
    except TokenError as error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(error))
    return session.astokens()


@router.post("/logout", response_model=schemas.MessageResponse)
def logout(body: schemas.RefreshRequest):
    Session.revoke(body.refresh_token)
    return {"message": "logged out"}


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return user_to_dict(user)
