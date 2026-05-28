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
