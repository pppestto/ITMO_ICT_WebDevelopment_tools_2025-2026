from datetime import datetime

from pydantic import BaseModel, Field

from app.models.task import Priority, TaskStatus
from app.schemas.category import CategoryRead
from app.schemas.tag import TaskTagLinkRead
from app.schemas.time_entry import TimeEntryRead


class TaskCreate(BaseModel):
    title: str = Field(max_length=200)
    description: str | None = None
    deadline: datetime | None = None
    priority: Priority = Priority.medium
    estimated_minutes: int | None = Field(default=None, ge=0)
    category_id: int | None = None


class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    deadline: datetime | None = None
    priority: Priority | None = None
    status: TaskStatus | None = None
    estimated_minutes: int | None = Field(default=None, ge=0)
    category_id: int | None = None


class TaskRead(BaseModel):
    id: int
    title: str
    description: str | None
    deadline: datetime | None
    priority: Priority
    status: TaskStatus
    estimated_minutes: int | None
    created_at: datetime
    updated_at: datetime
    owner_id: int
    category_id: int | None

    model_config = {"from_attributes": True}


class TaskReadDetail(TaskRead):
    category: CategoryRead | None = None
    tag_links: list[TaskTagLinkRead] = []
    time_entries: list[TimeEntryRead] = []


class DeadlineAlert(BaseModel):
    task_id: int
    title: str
    deadline: datetime
    hours_remaining: float
    priority: Priority
