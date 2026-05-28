from fastapi import APIRouter, HTTPException
from sqlmodel import select

from app.core.deps import CurrentUserDep, SessionDep
from app.models.user import User
from app.schemas.user import UserRead, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserRead)
def get_me(current_user: CurrentUserDep) -> User:
    return current_user


@router.patch("/me", response_model=UserRead)
def update_me(payload: UserUpdate, session: SessionDep, current_user: CurrentUserDep) -> User:
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(current_user, key, value)
    session.add(current_user)
    session.commit()
    session.refresh(current_user)
    return current_user


@router.get("/", response_model=list[UserRead])
def list_users(session: SessionDep, current_user: CurrentUserDep) -> list[User]:
    return list(session.exec(select(User)).all())


@router.get("/{user_id}", response_model=UserRead)
def get_user(user_id: int, session: SessionDep, current_user: CurrentUserDep) -> User:
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    return user
