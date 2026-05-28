from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.models.task import Task


class Tag(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True, max_length=80)

    task_links: list["TaskTagLink"] = Relationship(back_populates="tag")


class TaskTagLink(SQLModel, table=True):
    """Ассоциативная сущность many-to-many: задача ↔ тег."""

    task_id: Optional[int] = Field(default=None, foreign_key="task.id", primary_key=True)
    tag_id: Optional[int] = Field(default=None, foreign_key="tag.id", primary_key=True)
    relevance: int = Field(default=50, ge=0, le=100, description="Важность тега для задачи (0–100)")
    assigned_at: datetime = Field(default_factory=datetime.utcnow)

    task: "Task" = Relationship(back_populates="tag_links")
    tag: Tag = Relationship(back_populates="task_links")
