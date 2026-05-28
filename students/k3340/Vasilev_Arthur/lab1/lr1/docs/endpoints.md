# Эндпоинты API

Все маршруты (кроме `/health` и auth register/login) требуют заголовок:

```
Authorization: Bearer <access_token>
```

## Служебный

| Метод | Путь | Auth | Описание |
|-------|------|------|----------|
| `GET` | `/health` | — | Проверка работоспособности → `{"status": "ok"}` |

## Авторизация — `/api/auth`

| Метод | Путь | Auth | Тело запроса | Ответ |
|-------|------|------|--------------|-------|
| `POST` | `/register` | — | `UserRegister`: email, username, password, full_name? | `UserRead` (201) |
| `POST` | `/login` | — | OAuth2 form: username, password | `Token` |
| `POST` | `/login/json` | — | `UserLogin`: username, password | `Token` |
| `POST` | `/change-password` | Bearer | `PasswordChange`: current_password, new_password | 204 |

## Пользователи — `/api/users`

| Метод | Путь | Описание |
|-------|------|----------|
| `GET` | `/me` | Текущий пользователь |
| `PATCH` | `/me` | Обновление full_name, email |
| `GET` | `/` | Список всех пользователей |
| `GET` | `/{user_id}` | Пользователь по id |

## Категории — `/api/categories`

| Метод | Путь | Описание |
|-------|------|----------|
| `GET` | `/` | Список категорий |
| `GET` | `/{category_id}` | Категория по id |
| `POST` | `/` | Создание категории |
| `PATCH` | `/{category_id}` | Обновление |
| `DELETE` | `/{category_id}` | Удаление (204) |

## Теги — `/api/tags`

| Метод | Путь | Описание |
|-------|------|----------|
| `GET` | `/` | Список тегов |
| `GET` | `/{tag_id}` | Тег по id |
| `POST` | `/` | Создание тега |
| `DELETE` | `/{tag_id}` | Удаление (204) |

## Задачи — `/api/tasks`

| Метод | Путь | Описание |
|-------|------|----------|
| `GET` | `/` | Задачи текущего пользователя |
| `GET` | `/deadline-alerts?hours=48` | Задачи с приближающимся дедлайном |
| `GET` | `/time-analysis` | Анализ затраченного времени по задачам |
| `GET` | `/{task_id}` | Задача с category, tag_links, time_entries |
| `POST` | `/` | Создание задачи |
| `PATCH` | `/{task_id}` | Обновление задачи |
| `DELETE` | `/{task_id}` | Удаление (204) |
| `POST` | `/{task_id}/tags` | Привязка тега (relevance 0–100) |
| `DELETE` | `/{task_id}/tags/{tag_id}` | Отвязка тега (204) |

## Учёт времени — `/api/time-entries`

| Метод | Путь | Описание |
|-------|------|----------|
| `GET` | `/` | Записи по задачам текущего пользователя |
| `GET` | `/{entry_id}` | Запись по id |
| `POST` | `/` | Создание записи |
| `PATCH` | `/{entry_id}` | Обновление |
| `DELETE` | `/{entry_id}` | Удаление (204) |

## Расписание — `/api/schedules`

| Метод | Путь | Описание |
|-------|------|----------|
| `GET` | `/` | Расписания текущего пользователя |
| `GET` | `/{schedule_id}` | Расписание с items и задачами |
| `POST` | `/` | Создание расписания |
| `PATCH` | `/{schedule_id}` | Обновление |
| `DELETE` | `/{schedule_id}` | Удаление (204) |
| `POST` | `/{schedule_id}/items` | Добавить слот |
| `DELETE` | `/{schedule_id}/items/{item_id}` | Удалить слот (204) |

**Итого: 40 эндпоинтов** (1 health + 39 API)

---

## Код роутера

```python
# app/api/router.py
from fastapi import APIRouter

from app.api import auth, categories, schedules, tags, tasks, time_entries, users

api_router = APIRouter(prefix="/api")
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(categories.router)
api_router.include_router(tags.router)
api_router.include_router(tasks.router)
api_router.include_router(time_entries.router)
api_router.include_router(schedules.router)
```

## Код точки входа

```python
# app/main.py
from fastapi import FastAPI

from app.api.router import api_router

app = FastAPI(
    title="Time Manager API",
    description="Тайм-менеджер: задачи, дедлайны, учёт времени, расписание",
    version="1.0.0",
)

app.include_router(api_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
```

## Код авторизации

```python
# app/api/auth.py
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
```

[Исходники на GitHub → app/api/](https://github.com/pppestto/ITMO_ICT_WebDevelopment_tools_2025-2026/tree/lab1/students/k3340/Vasilev_Arthur/lab1/lr1/app/api)
