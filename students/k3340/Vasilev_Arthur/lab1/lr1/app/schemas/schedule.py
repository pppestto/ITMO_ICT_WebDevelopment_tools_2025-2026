from datetime import date, time

from pydantic import BaseModel, Field

from app.schemas.task import TaskRead


class ScheduleCreate(BaseModel):
    title: str = Field(max_length=200)
    schedule_date: date
    notes: str | None = None


class ScheduleUpdate(BaseModel):
    title: str | None = None
    schedule_date: date | None = None
    notes: str | None = None


class ScheduleItemCreate(BaseModel):
    task_id: int
    start_time: time
    end_time: time
    order_index: int = 0


class ScheduleItemRead(BaseModel):
    id: int
    start_time: time
    end_time: time
    order_index: int
    task_id: int
    schedule_id: int
    task: TaskRead

    model_config = {"from_attributes": True}


class ScheduleRead(BaseModel):
    id: int
    title: str
    schedule_date: date
    notes: str | None
    user_id: int

    model_config = {"from_attributes": True}


class ScheduleReadDetail(ScheduleRead):
    items: list[ScheduleItemRead] = []
