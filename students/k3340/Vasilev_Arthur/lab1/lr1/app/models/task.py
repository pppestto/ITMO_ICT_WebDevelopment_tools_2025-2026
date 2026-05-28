from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Optional

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.models.category import Category
    from app.models.schedule import ScheduleItem
    from app.models.tag import TaskTagLink
    from app.models.time_entry import TimeEntry
    from app.models.user import User


class Priority(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class TaskStatus(str, Enum):
    pending = "pending"
    in_progress = "in_progress"
    completed = "completed"
    cancelled = "cancelled"


class Task(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(max_length=200)
    description: Optional[str] = Field(default=None, max_length=2000)
    deadline: Optional[datetime] = Field(default=None)
    priority: Priority = Field(default=Priority.medium)
    status: TaskStatus = Field(default=TaskStatus.pending)
    estimated_minutes: Optional[int] = Field(default=None, ge=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    owner_id: int = Field(foreign_key="user.id")
    category_id: Optional[int] = Field(default=None, foreign_key="category.id")

    owner: "User" = Relationship(back_populates="tasks")
    category: Optional["Category"] = Relationship(back_populates="tasks")
    time_entries: list["TimeEntry"] = Relationship(back_populates="task")
    tag_links: list["TaskTagLink"] = Relationship(back_populates="task")
    schedule_items: list["ScheduleItem"] = Relationship(back_populates="task")
