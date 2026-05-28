from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException
from sqlalchemy.orm import selectinload
from sqlmodel import select

from app.core.deps import CurrentUserDep, SessionDep
from app.models.tag import Tag, TaskTagLink
from app.models.task import Task, TaskStatus
from app.schemas.tag import TaskTagLinkCreate, TaskTagLinkRead
from app.schemas.task import (
    DeadlineAlert,
    TaskCreate,
    TaskRead,
    TaskReadDetail,
    TaskUpdate,
)
from app.schemas.time_entry import TimeAnalysisReport

router = APIRouter(prefix="/tasks", tags=["tasks"])


def _get_user_task(session: SessionDep, task_id: int, user_id: int) -> Task:
    task = session.get(Task, task_id)
    if not task or task.owner_id != user_id:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    return task


@router.get("/", response_model=list[TaskRead])
def list_tasks(session: SessionDep, current_user: CurrentUserDep) -> list[Task]:
    return list(
        session.exec(select(Task).where(Task.owner_id == current_user.id)).all()
    )


@router.get("/deadline-alerts", response_model=list[DeadlineAlert])
def deadline_alerts(
    session: SessionDep,
    current_user: CurrentUserDep,
    hours: int = 48,
) -> list[DeadlineAlert]:
    """Уведомления о задачах с приближающимся дедлайном."""
    now = datetime.utcnow()
    threshold = now + timedelta(hours=hours)
    tasks = session.exec(
        select(Task).where(
            Task.owner_id == current_user.id,
            Task.deadline.is_not(None),
            Task.deadline > now,
            Task.deadline <= threshold,
            Task.status != TaskStatus.completed,
            Task.status != TaskStatus.cancelled,
        )
    ).all()
    alerts: list[DeadlineAlert] = []
    for task in tasks:
        assert task.deadline is not None
        remaining = (task.deadline - now).total_seconds() / 3600
        alerts.append(
            DeadlineAlert(
                task_id=task.id,
                title=task.title,
                deadline=task.deadline,
                hours_remaining=round(remaining, 2),
                priority=task.priority,
            )
        )
    return alerts


@router.get("/time-analysis", response_model=TimeAnalysisReport)
def time_analysis(session: SessionDep, current_user: CurrentUserDep) -> TimeAnalysisReport:
    from app.models.time_entry import TimeEntry

    tasks = session.exec(select(Task).where(Task.owner_id == current_user.id)).all()
    by_task = []
    total = 0
    for task in tasks:
        entries = session.exec(select(TimeEntry).where(TimeEntry.task_id == task.id)).all()
        minutes = sum(e.duration_minutes or 0 for e in entries)
        total += minutes
        by_task.append(
            {
                "task_id": task.id,
                "task_title": task.title,
                "total_minutes": minutes,
                "entries_count": len(entries),
            }
        )
    from app.schemas.time_entry import TimeAnalysisItem

    return TimeAnalysisReport(
        user_id=current_user.id,
        total_minutes=total,
        by_task=[TimeAnalysisItem(**item) for item in by_task],
    )


@router.get("/{task_id}", response_model=TaskReadDetail)
def get_task(task_id: int, session: SessionDep, current_user: CurrentUserDep) -> Task:
    statement = (
        select(Task)
        .where(Task.id == task_id, Task.owner_id == current_user.id)
        .options(
            selectinload(Task.category),
            selectinload(Task.tag_links).selectinload(TaskTagLink.tag),
            selectinload(Task.time_entries),
        )
    )
    task = session.exec(statement).first()
    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    return task


@router.post("/", response_model=TaskRead, status_code=201)
def create_task(
    payload: TaskCreate, session: SessionDep, current_user: CurrentUserDep
) -> Task:
    task = Task(**payload.model_dump(), owner_id=current_user.id)
    session.add(task)
    session.commit()
    session.refresh(task)
    return task


@router.patch("/{task_id}", response_model=TaskRead)
def update_task(
    task_id: int,
    payload: TaskUpdate,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> Task:
    task = _get_user_task(session, task_id, current_user.id)
    data = payload.model_dump(exclude_unset=True)
    data["updated_at"] = datetime.utcnow()
    for key, value in data.items():
        setattr(task, key, value)
    session.add(task)
    session.commit()
    session.refresh(task)
    return task


@router.delete("/{task_id}", status_code=204)
def delete_task(
    task_id: int, session: SessionDep, current_user: CurrentUserDep
) -> None:
    task = _get_user_task(session, task_id, current_user.id)
    session.delete(task)
    session.commit()


@router.post("/{task_id}/tags", response_model=TaskTagLinkRead, status_code=201)
def attach_tag(
    task_id: int,
    payload: TaskTagLinkCreate,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> TaskTagLink:
    task = _get_user_task(session, task_id, current_user.id)
    tag = session.get(Tag, payload.tag_id)
    if not tag:
        raise HTTPException(status_code=404, detail="Тег не найден")
    existing = session.get(TaskTagLink, (task_id, payload.tag_id))
    if existing:
        raise HTTPException(status_code=400, detail="Тег уже привязан к задаче")
    link = TaskTagLink(task_id=task.id, tag_id=payload.tag_id, relevance=payload.relevance)
    session.add(link)
    session.commit()
    session.refresh(link)
    link = session.exec(
        select(TaskTagLink)
        .where(TaskTagLink.task_id == task_id, TaskTagLink.tag_id == payload.tag_id)
        .options(selectinload(TaskTagLink.tag))
    ).one()
    return link


@router.delete("/{task_id}/tags/{tag_id}", status_code=204)
def detach_tag(
    task_id: int, tag_id: int, session: SessionDep, current_user: CurrentUserDep
) -> None:
    _get_user_task(session, task_id, current_user.id)
    link = session.get(TaskTagLink, (task_id, tag_id))
    if not link:
        raise HTTPException(status_code=404, detail="Связь не найдена")
    session.delete(link)
    session.commit()
