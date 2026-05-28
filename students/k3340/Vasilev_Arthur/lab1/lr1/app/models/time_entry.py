from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.models.task import Task


class TimeEntry(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    started_at: datetime
    ended_at: Optional[datetime] = Field(default=None)
    duration_minutes: Optional[int] = Field(default=None, ge=0)
    note: Optional[str] = Field(default=None, max_length=500)

    task_id: int = Field(foreign_key="task.id")

    task: "Task" = Relationship(back_populates="time_entries")
