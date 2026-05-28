# LR1 — Time Manager API: подробный разбор для защиты

**Студент:** Васильев Arthur  
**Группа:** k3340  
**Стек:** FastAPI · SQLModel · PostgreSQL · Alembic · JWT · Docker

---

## 1. Что делает проект

Это REST API **тайм-менеджера**: пользователи регистрируются, получают JWT-токен и через защищённые эндпоинты управляют задачами, категориями, тегами, учётом времени и ежедневным расписанием.

**Ключевые требования лабораторной, которые закрыты:**
- 8 таблиц в PostgreSQL
- Связи one-to-many и many-to-many (через ассоциативную таблицу `TaskTagLink` с полем `relevance`)
- CRUD по сущностям
- JWT-авторизация (регистрация, логин, смена пароля)
- Миграции Alembic
- Docker Compose для запуска «в один клик»
- Доп. функционал: дедлайн-алерты, анализ времени, вложенные ответы

---

## 2. Общий flow приложения

```mermaid
sequenceDiagram
    participant Client
    participant FastAPI
    participant Deps as deps.py
    participant Security as security.py
    participant DB as PostgreSQL

    Client->>FastAPI: POST /api/auth/register
    FastAPI->>Security: get_password_hash()
    FastAPI->>DB: INSERT user
    FastAPI-->>Client: UserRead (201)

    Client->>FastAPI: POST /api/auth/login (form/json)
    FastAPI->>DB: SELECT user by username
    FastAPI->>Security: verify_password()
    FastAPI->>Security: create_access_token(user.id)
    FastAPI-->>Client: { access_token, token_type: bearer }

    Client->>FastAPI: GET /api/tasks/ + Authorization: Bearer ...
    FastAPI->>Deps: get_current_user()
    Deps->>Security: decode_access_token()
    Deps->>DB: SELECT user by id
    FastAPI->>DB: SELECT tasks WHERE owner_id = user.id
    FastAPI-->>Client: list[TaskRead]
```

### Пошагово при запуске

1. **Docker Compose** поднимает PostgreSQL (`db`) и ждёт healthcheck.
2. Контейнер **API** собирается из `Dockerfile`, выполняет `alembic upgrade head`, затем `uvicorn app.main:app`.
3. **FastAPI** в `app/main.py` создаёт приложение и подключает `api_router` с префиксом `/api`.
4. Каждый запрос к защищённому маршруту проходит через `CurrentUserDep` → извлекается Bearer-токен → декодируется JWT → загружается пользователь из БД.
5. **SQLModel Session** создаётся через `get_session()` (dependency injection) и автоматически закрывается после ответа.

### Пример типичного сценария пользователя

1. `POST /api/auth/register` — создать аккаунт
2. `POST /api/auth/login` — получить JWT
3. `POST /api/categories/` — создать категорию «Учёба»
4. `POST /api/tasks/` — создать задачу с дедлайном
5. `POST /api/tags/` + `POST /api/tasks/{id}/tags` — привязать тег с relevance
6. `POST /api/time-entries/` — записать затраченное время
7. `GET /api/tasks/deadline-alerts?hours=48` — проверить приближающиеся дедлайны
8. `POST /api/schedules/` + `POST /api/schedules/{id}/items` — составить расписание на день

---

## 3. Структура папок и файлов

```
lr1/
├── app/                    # Исходный код приложения
│   ├── main.py             # Точка входа FastAPI
│   ├── api/                # HTTP-маршруты (роутеры)
│   ├── core/               # Конфиг, JWT, зависимости
│   ├── db/                 # Подключение к PostgreSQL
│   ├── models/             # SQLModel-модели (таблицы БД)
│   └── schemas/            # Pydantic-схемы (вход/выход API)
├── migrations/             # Alembic: env.py + версии миграций
├── docs/                   # Отчёт для GitHub Pages (MkDocs)
├── alembic.ini             # Конфиг Alembic
├── docker-compose.yml      # PostgreSQL + API
├── Dockerfile              # Сборка образа API
├── requirements.txt        # Python-зависимости
├── .env.example            # Шаблон переменных окружения
├── README.md               # Краткая инструкция по запуску
└── DEFENSE_GUIDE.md        # Этот файл
```

---

## 4. Корневые файлы (вне `app/`)

| Файл | Назначение |
|------|------------|
| `requirements.txt` | fastapi, uvicorn, sqlmodel, psycopg2-binary, alembic, passlib, python-jose, pydantic-settings, email-validator, python-multipart |
| `alembic.ini` | Базовые настройки Alembic (путь к migrations, logging) |
| `docker-compose.yml` | Сервис `db` (Postgres 16) + `api` (FastAPI). Переменные `DB_ADMIN`, `JWT_SECRET` передаются в контейнер API |
| `Dockerfile` | Python 3.11-slim, установка зависимостей, копирование `app/` и `migrations/`, entrypoint: миграции + uvicorn |
| `.env.example` | Шаблон: `DB_ADMIN`, `JWT_SECRET`, `JWT_ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES` |
| `.gitignore` | Исключает `.env`, `venv/`, `__pycache__/` |
| `.dockerignore` | Исключает лишнее из Docker-контекста |

---

## 5. Папка `app/` — ядро приложения

### `app/main.py`

Создаёт экземпляр `FastAPI` с title/description/version. Подключает `api_router` из `app/api/router.py`. Добавляет служебный эндпоинт `GET /health` → `{"status": "ok"}`.

### `app/__init__.py`

Пустой файл — помечает `app` как Python-пакет.

---

## 6. Папка `app/core/` — конфигурация и безопасность

### `app/core/config.py`

Класс `Settings` (Pydantic BaseSettings):
- `db_url` — из `DB_ADMIN`
- `jwt_secret`, `jwt_algorithm`, `access_token_expire_minutes`

Функция `get_settings()` с `@lru_cache` — настройки читаются один раз.

### `app/core/security.py`

- `pwd_context` — bcrypt через passlib
- `verify_password()` / `get_password_hash()` — проверка и хеширование паролей
- `create_access_token(subject)` — JWT с полями `sub` (id пользователя) и `exp`
- `decode_access_token(token)` — декодирование; при ошибке возвращает `None`

### `app/core/deps.py`

Зависимости FastAPI (Dependency Injection):

| Alias | Что делает |
|-------|------------|
| `SessionDep` | Выдаёт SQLModel `Session` из `get_session()` |
| `TokenDep` | Извлекает Bearer-токен из заголовка `Authorization` |
| `CurrentUserDep` | Декодирует JWT → загружает `User` из БД → проверяет `is_active` |

`OAuth2PasswordBearer(tokenUrl="/api/auth/login")` — для Swagger UI кнопки «Authorize».

---

## 7. Папка `app/db/` — подключение к БД

### `app/db/connection.py`

```python
load_dotenv()
db_url = os.getenv("DB_ADMIN", "postgresql://postgres:123@localhost/time_manager_db")
engine = create_engine(db_url, echo=False)

def get_session() -> Session:
    with Session(engine) as session:
        yield session
```

- Читает URL из `.env` (переменная `DB_ADMIN`)
- Создаёт SQLAlchemy engine
- `get_session()` — генератор для FastAPI Depends: открывает сессию на запрос, закрывает после

---

## 8. Папка `app/models/` — модели БД (SQLModel)

Все модели наследуют `SQLModel, table=True` — одновременно ORM-модель и схема Pydantic.

### `user.py` — таблица `user`

| Поле | Тип | Описание |
|------|-----|----------|
| id | int PK | Автоинкремент |
| email | str, unique | Email |
| username | str, unique | Логин |
| hashed_password | str | Bcrypt-хеш |
| full_name | str? | ФИО |
| is_active | bool | Активен ли аккаунт |
| created_at | datetime | Дата регистрации |

**Связи:** `tasks` (1→N), `schedules` (1→N)

### `category.py` — таблица `category`

| Поле | Тип |
|------|-----|
| id | int PK |
| name | str, unique |
| description | str? |
| color | str? (hex, default `#3498db`) |

**Связь:** `tasks` (1→N)

### `task.py` — таблица `task`

Enums: `Priority` (low/medium/high/critical), `TaskStatus` (pending/in_progress/completed/cancelled)

| Поле | Тип |
|------|-----|
| title, description, deadline | |
| priority, status | enums |
| estimated_minutes | int? |
| created_at, updated_at | datetime |
| owner_id | FK → user.id |
| category_id | FK → category.id (nullable) |

**Связи:** owner, category, time_entries, tag_links, schedule_items

### `tag.py` — таблицы `tag` и `tasktaglink`

**Tag:** id, name (unique)

**TaskTagLink** — ассоциативная M2M-сущность:
- Составной PK: `(task_id, tag_id)`
- `relevance` int 0–100 — «важность» тега для задачи
- `assigned_at` datetime

### `time_entry.py` — таблица `timeentry`

Учёт времени по задаче: started_at, ended_at, duration_minutes, note, task_id (FK).

### `schedule.py` — таблицы `schedule` и `scheduleitem`

**Schedule:** title, schedule_date (date), notes, user_id (FK)

**ScheduleItem:** start_time, end_time, order_index, schedule_id, task_id (FK)

### `models/__init__.py`

Реэкспорт всех моделей для Alembic (`from app.models import *` в `migrations/env.py`).

---

## 9. Папка `app/schemas/` — Pydantic-схемы API

Схемы отделены от моделей: модели = БД, схемы = контракт API.

| Файл | Схемы |
|------|-------|
| `auth.py` | UserRegister, UserLogin, Token, PasswordChange |
| `user.py` | UserRead, UserUpdate |
| `category.py` | CategoryCreate, CategoryUpdate, CategoryRead |
| `tag.py` | TagCreate, TagRead, TaskTagLinkCreate, TaskTagLinkRead |
| `task.py` | TaskCreate, TaskUpdate, TaskRead, TaskReadDetail, DeadlineAlert |
| `time_entry.py` | TimeEntryCreate/Update/Read, TimeAnalysisItem, TimeAnalysisReport |
| `schedule.py` | ScheduleCreate/Update/Read/ReadDetail, ScheduleItemCreate/Read |

`model_config = {"from_attributes": True}` — позволяет создавать схему из ORM-объекта.

**TaskReadDetail** и **ScheduleReadDetail** — «богатые» ответы с вложенными объектами (категория, теги, time entries, items расписания).

---

## 10. Папка `app/api/` — эндпоинты

### `router.py`

Собирает все роутеры под префиксом `/api`.

### `auth.py` — `/api/auth`

| Метод | Путь | Auth | Описание |
|-------|------|------|----------|
| POST | /register | — | Регистрация, проверка уникальности email/username |
| POST | /login | — | OAuth2 form (username+password) → JWT |
| POST | /login/json | — | То же через JSON body |
| POST | /change-password | Bearer | Смена пароля |

### `users.py` — `/api/users`

| Метод | Путь | Описание |
|-------|------|----------|
| GET | /me | Текущий пользователь |
| PATCH | /me | Обновить full_name/email |
| GET | / | Список всех пользователей |
| GET | /{user_id} | Пользователь по id |

### `categories.py` — `/api/categories`

Полный CRUD: list, get, create, update, delete.

### `tags.py` — `/api/tags`

List, get, create, delete (без update — по заданию достаточно).

### `tasks.py` — `/api/tasks`

| Метод | Путь | Особенности |
|-------|------|-------------|
| GET | / | Только задачи текущего пользователя |
| GET | /deadline-alerts | Задачи с дедлайном в ближайшие N часов (default 48) |
| GET | /time-analysis | Сумма минут по каждой задаче |
| GET | /{id} | Детальный ответ с category, tag_links, time_entries (selectinload) |
| POST/PATCH/DELETE | /, /{id} | CRUD с проверкой owner_id |
| POST | /{id}/tags | Привязать тег + relevance |
| DELETE | /{id}/tags/{tag_id} | Отвязать тег |

### `time_entries.py` — `/api/time-entries`

CRUD записей времени. Доступ только к записям своих задач (`_ensure_task_access`).

### `schedules.py` — `/api/schedules`

CRUD расписаний + `POST /{id}/items` и `DELETE /{id}/items/{item_id}`.  
`GET /{id}` возвращает items с вложенными задачами.

---

## 11. Миграции Alembic

### `migrations/env.py`

- Добавляет корень проекта в `sys.path`
- Импортирует все модели → `target_metadata = SQLModel.metadata`
- Подставляет `DB_ADMIN` из `.env` в `sqlalchemy.url`
- Режимы offline/online миграций

### `migrations/versions/001_initial_schema.py`

Создаёт все 8 таблиц, индексы, FK, enum-типы `priority` и `taskstatus`.  
`downgrade()` удаляет таблицы в обратном порядке.

---

## 12. Диаграмма связей БД

```mermaid
erDiagram
    USER ||--o{ TASK : owns
    USER ||--o{ SCHEDULE : has
    CATEGORY ||--o{ TASK : contains
    TASK ||--o{ TIMEENTRY : tracks
    TASK ||--o{ SCHEDULEITEM : scheduled_in
    SCHEDULE ||--o{ SCHEDULEITEM : contains
    TASK ||--o{ TASKTAGLINK : has
    TAG ||--o{ TASKTAGLINK : linked
```

---

## 13. Безопасность и изоляция данных

- Пароли **никогда** не хранятся в открытом виде — только bcrypt-хеш
- JWT содержит только `sub` (user id) и `exp`
- Задачи фильтруются по `owner_id == current_user.id`
- Time entries проверяют принадлежность задачи пользователю
- Расписания фильтруются по `user_id`

---

## 14. Что говорить на защите (шпаргалка)

1. **Почему SQLModel?** — объединяет SQLAlchemy ORM и Pydantic; меньше дублирования кода.
2. **Почему Alembic, а не `create_all()`?** — версионирование схемы, безопасные изменения в production.
3. **M2M через TaskTagLink** — не простая связующая таблица, а сущность с доп. полями (`relevance`, `assigned_at`).
4. **selectinload** — eager loading для избежания N+1 запросов в детальных GET.
5. **Docker Compose** — изолированная среда, healthcheck БД перед стартом API.
6. **Два способа логина** — form (стандарт OAuth2 для Swagger) и JSON (удобнее для фронтенда).

---

## 15. Запуск для демонстрации

```bash
cd lr1
docker compose up --build
```

Открыть: http://127.0.0.1:8000/docs

1. Register → Login → Authorize (вставить token)
2. Создать category → task → tag → привязать tag
3. Показать deadline-alerts и time-analysis

---

## 16. Ссылки на GitHub

> ⚠️ Закоммитьте и запушьте код перед защитой, чтобы ссылки работали.

| Ресурс | URL |
|--------|-----|
| Репозиторий | https://github.com/pppestto/ITMO_ICT_WebDevelopment_tools_2025-2026 |
| Ветка lab1 | https://github.com/pppestto/ITMO_ICT_WebDevelopment_tools_2025-2026/tree/lab1 |
| LR1 (финальный проект) | https://github.com/pppestto/ITMO_ICT_WebDevelopment_tools_2025-2026/tree/lab1/students/k3340/Vasilev_Arthur/lab1/lr1 |
| Практика 1 (pr1) | https://github.com/pppestto/ITMO_ICT_WebDevelopment_tools_2025-2026/tree/lab1/students/k3340/Vasilev_Arthur/lab1/pr1 |
| Практика 2 (pr2) | https://github.com/pppestto/ITMO_ICT_WebDevelopment_tools_2025-2026/tree/lab1/students/k3340/Vasilev_Arthur/lab1/pr2 |
| Практика 3 (pr3) | https://github.com/pppestto/ITMO_ICT_WebDevelopment_tools_2025-2026/tree/lab1/students/k3340/Vasilev_Arthur/lab1/pr3 |
| Отчёт (GitHub Pages) | https://pppestto.github.io/ITMO_ICT_WebDevelopment_tools_2025-2026/ *(после деплоя MkDocs)* |
