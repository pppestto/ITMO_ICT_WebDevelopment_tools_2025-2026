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
