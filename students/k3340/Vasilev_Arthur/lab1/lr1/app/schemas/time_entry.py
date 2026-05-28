from datetime import datetime

from pydantic import BaseModel, Field


class TimeEntryCreate(BaseModel):
    task_id: int
    started_at: datetime
    ended_at: datetime | None = None
    duration_minutes: int | None = Field(default=None, ge=0)
    note: str | None = None


class TimeEntryUpdate(BaseModel):
    ended_at: datetime | None = None
    duration_minutes: int | None = Field(default=None, ge=0)
    note: str | None = None


class TimeEntryRead(BaseModel):
    id: int
    started_at: datetime
    ended_at: datetime | None
    duration_minutes: int | None
    note: str | None
    task_id: int

    model_config = {"from_attributes": True}


class TimeAnalysisItem(BaseModel):
    task_id: int
    task_title: str
    total_minutes: int
    entries_count: int


class TimeAnalysisReport(BaseModel):
    user_id: int
    total_minutes: int
    by_task: list[TimeAnalysisItem]
