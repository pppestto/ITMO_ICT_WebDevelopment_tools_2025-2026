from datetime import datetime

from pydantic import BaseModel, Field


class TagCreate(BaseModel):
    name: str = Field(max_length=80)


class TagRead(BaseModel):
    id: int
    name: str

    model_config = {"from_attributes": True}


class TaskTagLinkCreate(BaseModel):
    tag_id: int
    relevance: int = Field(default=50, ge=0, le=100)


class TaskTagLinkRead(BaseModel):
    task_id: int
    tag_id: int
    relevance: int
    assigned_at: datetime
    tag: TagRead

    model_config = {"from_attributes": True}
