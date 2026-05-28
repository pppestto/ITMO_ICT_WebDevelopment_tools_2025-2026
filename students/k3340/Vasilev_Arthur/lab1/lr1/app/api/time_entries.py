from fastapi import APIRouter, HTTPException
from sqlmodel import select

from app.core.deps import CurrentUserDep, SessionDep
from app.models.task import Task
from app.models.time_entry import TimeEntry
from app.schemas.time_entry import TimeEntryCreate, TimeEntryRead, TimeEntryUpdate

router = APIRouter(prefix="/time-entries", tags=["time-entries"])


def _ensure_task_access(session: SessionDep, task_id: int, user_id: int) -> Task:
    task = session.get(Task, task_id)
    if not task or task.owner_id != user_id:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    return task


@router.get("/", response_model=list[TimeEntryRead])
def list_time_entries(session: SessionDep, current_user: CurrentUserDep) -> list[TimeEntry]:
    task_ids = [
        t.id
        for t in session.exec(select(Task).where(Task.owner_id == current_user.id)).all()
    ]
    if not task_ids:
        return []
    return list(session.exec(select(TimeEntry).where(TimeEntry.task_id.in_(task_ids))).all())


@router.get("/{entry_id}", response_model=TimeEntryRead)
def get_time_entry(
    entry_id: int, session: SessionDep, current_user: CurrentUserDep
) -> TimeEntry:
    entry = session.get(TimeEntry, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Запись не найдена")
    _ensure_task_access(session, entry.task_id, current_user.id)
    return entry


@router.post("/", response_model=TimeEntryRead, status_code=201)
def create_time_entry(
    payload: TimeEntryCreate, session: SessionDep, current_user: CurrentUserDep
) -> TimeEntry:
    _ensure_task_access(session, payload.task_id, current_user.id)
    entry = TimeEntry(**payload.model_dump())
    session.add(entry)
    session.commit()
    session.refresh(entry)
    return entry


@router.patch("/{entry_id}", response_model=TimeEntryRead)
def update_time_entry(
    entry_id: int,
    payload: TimeEntryUpdate,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> TimeEntry:
    entry = session.get(TimeEntry, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Запись не найдена")
    _ensure_task_access(session, entry.task_id, current_user.id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(entry, key, value)
    session.add(entry)
    session.commit()
    session.refresh(entry)
    return entry


@router.delete("/{entry_id}", status_code=204)
def delete_time_entry(
    entry_id: int, session: SessionDep, current_user: CurrentUserDep
) -> None:
    entry = session.get(TimeEntry, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Запись не найдена")
    _ensure_task_access(session, entry.task_id, current_user.id)
    session.delete(entry)
    session.commit()
