from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, select

from app.core.deps import CurrentUserDep, SessionDep
from app.core.security import create_access_token, get_password_hash, verify_password
from app.models.user import User
from app.schemas.auth import PasswordChange, Token, UserLogin, UserRegister
from app.schemas.user import UserRead

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(payload: UserRegister, session: SessionDep) -> User:
    existing = session.exec(
        select(User).where((User.email == payload.email) | (User.username == payload.username))
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email или имя пользователя уже заняты")

    user = User(
        email=payload.email,
        username=payload.username,
        hashed_password=get_password_hash(payload.password),
        full_name=payload.full_name,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@router.post("/login", response_model=Token)
def login(form_data: Annotated[OAuth2PasswordRequestForm, Depends()], session: SessionDep) -> Token:
    user = session.exec(select(User).where(User.username == form_data.username)).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверное имя пользователя или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Аккаунт деактивирован")
    token = create_access_token(user.id)
    return Token(access_token=token)


@router.post("/login/json", response_model=Token)
def login_json(payload: UserLogin, session: SessionDep) -> Token:
    user = session.exec(select(User).where(User.username == payload.username)).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Неверное имя пользователя или пароль")
    return Token(access_token=create_access_token(user.id))


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(payload: PasswordChange, session: SessionDep, current_user: CurrentUserDep) -> None:
    if not verify_password(payload.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Текущий пароль указан неверно")
    current_user.hashed_password = get_password_hash(payload.new_password)
    session.add(current_user)
    session.commit()
