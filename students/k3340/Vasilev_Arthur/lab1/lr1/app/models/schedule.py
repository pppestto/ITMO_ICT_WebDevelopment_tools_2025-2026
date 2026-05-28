from datetime import date, time
from typing import TYPE_CHECKING, Optional

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.models.task import Task
    from app.models.user import User


class Schedule(SQLModel, table=True):
    """Ежедневное расписание пользователя."""

    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(max_length=200)
    schedule_date: date
    notes: Optional[str] = Field(default=None, max_length=1000)

    user_id: int = Field(foreign_key="user.id")

    user: "User" = Relationship(back_populates="schedules")
    items: list["ScheduleItem"] = Relationship(back_populates="schedule")


class ScheduleItem(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    start_time: time
    end_time: time
    order_index: int = Field(default=0, ge=0)

    schedule_id: int = Field(foreign_key="schedule.id")
    task_id: int = Field(foreign_key="task.id")

    schedule: Schedule = Relationship(back_populates="items")
    task: "Task" = Relationship(back_populates="schedule_items")
