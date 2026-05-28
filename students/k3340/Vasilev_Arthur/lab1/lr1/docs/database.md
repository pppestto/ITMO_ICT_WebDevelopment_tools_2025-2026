# Подключение к базе данных

## Переменные окружения

Файл `.env.example`:

```env
DB_ADMIN=postgresql://postgres:123@localhost/time_manager_db
JWT_SECRET=change-me-to-a-long-random-secret-key
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
```

В Docker (`docker-compose.yml`) для API:

```yaml
DB_ADMIN: postgresql://postgres:123@db:5432/time_manager_db
```

---

## Код соединения — `app/db/connection.py`

```python
import os

from dotenv import load_dotenv
from sqlmodel import Session, create_engine

load_dotenv()

db_url = os.getenv("DB_ADMIN", "postgresql://postgres:123@localhost/time_manager_db")

engine = create_engine(db_url, echo=False)


def get_session() -> Session:
    with Session(engine) as session:
        yield session
```

**Как это работает:**

1. `load_dotenv()` — загружает `.env`
2. `create_engine(db_url)` — создаёт пул соединений SQLAlchemy
3. `get_session()` — генератор для FastAPI Depends: одна сессия на HTTP-запрос

---

## Конфигурация — `app/core/config.py`

```python
import os
from functools import lru_cache

from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()


class Settings(BaseSettings):
    db_url: str = os.getenv("DB_ADMIN", "postgresql://postgres:123@localhost/time_manager_db")
    jwt_secret: str = os.getenv("JWT_SECRET", "dev-secret-change-in-production")
    jwt_algorithm: str = os.getenv("JWT_ALGORITHM", "HS256")
    access_token_expire_minutes: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

---

## Dependency Injection — `app/core/deps.py`

```python
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import Session, select

from app.core.security import decode_access_token
from app.db.connection import get_session
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

SessionDep = Annotated[Session, Depends(get_session)]
TokenDep = Annotated[str, Depends(oauth2_scheme)]


def get_current_user(session: SessionDep, token: TokenDep) -> User:
    user_id = decode_access_token(token)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Недействительный или просроченный токен",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = session.get(User, int(user_id))
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Пользователь не найден или деактивирован",
        )
    return user


CurrentUserDep = Annotated[User, Depends(get_current_user)]
```

---

## JWT и пароли — `app/core/security.py`

```python
from datetime import datetime, timedelta
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(subject: str | int, expires_delta: timedelta | None = None) -> str:
    settings = get_settings()
    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    payload: dict[str, Any] = {"sub": str(subject), "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> str | None:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        sub = payload.get("sub")
        return str(sub) if sub is not None else None
    except JWTError:
        return None
```

---

## Alembic — `migrations/env.py`

```python
import os
import sys
from logging.config import fileConfig

from alembic import context
from dotenv import load_dotenv
from sqlalchemy import engine_from_config, pool
from sqlmodel import SQLModel

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models import *  # noqa: F401, F403

load_dotenv()

config = context.config

db_url = os.getenv("DB_ADMIN")
if db_url:
    config.set_main_option("sqlalchemy.url", db_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = SQLModel.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

---

## Начальная миграция

Миграция `001_initial_schema` создаёт все 8 таблиц:

- `user`, `category`, `tag`, `task`
- `tasktaglink` (M2M с `relevance`)
- `timeentry`
- `schedule`, `scheduleitem`

Enum-типы PostgreSQL: `priority`, `taskstatus`.

Команды:

```bash
alembic upgrade head          # применить миграции
alembic revision --autogenerate -m "описание"  # новая миграция
```

В Docker миграции применяются автоматически при старте контейнера:

```dockerfile
ENTRYPOINT ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port 8000"]
```

[Исходники на GitHub → app/db/](https://github.com/pppestto/ITMO_ICT_WebDevelopment_tools_2025-2026/tree/lab1/students/k3340/Vasilev_Arthur/lab1/lr1/app/db)  
[Миграции → migrations/](https://github.com/pppestto/ITMO_ICT_WebDevelopment_tools_2025-2026/tree/lab1/students/k3340/Vasilev_Arthur/lab1/lr1/migrations)
