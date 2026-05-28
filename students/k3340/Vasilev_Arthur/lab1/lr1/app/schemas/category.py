from pydantic import BaseModel, Field


class CategoryCreate(BaseModel):
    name: str = Field(max_length=100)
    description: str | None = None
    color: str | None = "#3498db"


class CategoryUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    color: str | None = None


class CategoryRead(BaseModel):
    id: int
    name: str
    description: str | None
    color: str | None

    model_config = {"from_attributes": True}
