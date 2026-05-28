from fastapi import APIRouter, HTTPException
from sqlalchemy.orm import selectinload
from sqlmodel import select

from app.core.deps import CurrentUserDep, SessionDep
from app.models.schedule import Schedule, ScheduleItem
from app.models.task import Task
from app.schemas.schedule import (
    ScheduleCreate,
    ScheduleItemCreate,
    ScheduleItemRead,
    ScheduleRead,
    ScheduleReadDetail,
    ScheduleUpdate,
)

router = APIRouter(prefix="/schedules", tags=["schedules"])


@router.get("/", response_model=list[ScheduleRead])
def list_schedules(session: SessionDep, current_user: CurrentUserDep) -> list[Schedule]:
    return list(
        session.exec(select(Schedule).where(Schedule.user_id == current_user.id)).all()
    )


@router.get("/{schedule_id}", response_model=ScheduleReadDetail)
def get_schedule(
    schedule_id: int, session: SessionDep, current_user: CurrentUserDep
) -> Schedule:
    statement = (
        select(Schedule)
        .where(Schedule.id == schedule_id, Schedule.user_id == current_user.id)
        .options(
            selectinload(Schedule.items).selectinload(ScheduleItem.task),
        )
    )
    schedule = session.exec(statement).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Расписание не найдено")
    return schedule


@router.post("/", response_model=ScheduleRead, status_code=201)
def create_schedule(
    payload: ScheduleCreate, session: SessionDep, current_user: CurrentUserDep
) -> Schedule:
    schedule = Schedule(**payload.model_dump(), user_id=current_user.id)
    session.add(schedule)
    session.commit()
    session.refresh(schedule)
    return schedule


@router.patch("/{schedule_id}", response_model=ScheduleRead)
def update_schedule(
    schedule_id: int,
    payload: ScheduleUpdate,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> Schedule:
    schedule = session.get(Schedule, schedule_id)
    if not schedule or schedule.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Расписание не найдено")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(schedule, key, value)
    session.add(schedule)
    session.commit()
    session.refresh(schedule)
    return schedule


@router.delete("/{schedule_id}", status_code=204)
def delete_schedule(
    schedule_id: int, session: SessionDep, current_user: CurrentUserDep
) -> None:
    schedule = session.get(Schedule, schedule_id)
    if not schedule or schedule.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Расписание не найдено")
    session.delete(schedule)
    session.commit()


@router.post("/{schedule_id}/items", response_model=ScheduleItemRead, status_code=201)
def add_schedule_item(
    schedule_id: int,
    payload: ScheduleItemCreate,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> ScheduleItem:
    schedule = session.get(Schedule, schedule_id)
    if not schedule or schedule.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Расписание не найдено")
    task = session.get(Task, payload.task_id)
    if not task or task.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    item = ScheduleItem(**payload.model_dump(), schedule_id=schedule_id)
    session.add(item)
    session.commit()
    session.refresh(item)
    item = session.exec(
        select(ScheduleItem)
        .where(ScheduleItem.id == item.id)
        .options(selectinload(ScheduleItem.task))
    ).one()
    return item


@router.delete("/{schedule_id}/items/{item_id}", status_code=204)
def remove_schedule_item(
    schedule_id: int,
    item_id: int,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> None:
    schedule = session.get(Schedule, schedule_id)
    if not schedule or schedule.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Расписание не найдено")
    item = session.get(ScheduleItem, item_id)
    if not item or item.schedule_id != schedule_id:
        raise HTTPException(status_code=404, detail="Элемент расписания не найден")
    session.delete(item)
    session.commit()
