from fastapi import APIRouter, HTTPException
from sqlmodel import select

from app.core.deps import CurrentUserDep, SessionDep
from app.models.tag import Tag
from app.schemas.tag import TagCreate, TagRead

router = APIRouter(prefix="/tags", tags=["tags"])


@router.get("/", response_model=list[TagRead])
def list_tags(session: SessionDep, current_user: CurrentUserDep) -> list[Tag]:
    return list(session.exec(select(Tag)).all())


@router.get("/{tag_id}", response_model=TagRead)
def get_tag(tag_id: int, session: SessionDep, current_user: CurrentUserDep) -> Tag:
    tag = session.get(Tag, tag_id)
    if not tag:
        raise HTTPException(status_code=404, detail="Тег не найден")
    return tag


@router.post("/", response_model=TagRead, status_code=201)
def create_tag(payload: TagCreate, session: SessionDep, current_user: CurrentUserDep) -> Tag:
    tag = Tag(**payload.model_dump())
    session.add(tag)
    session.commit()
    session.refresh(tag)
    return tag


@router.delete("/{tag_id}", status_code=204)
def delete_tag(tag_id: int, session: SessionDep, current_user: CurrentUserDep) -> None:
    tag = session.get(Tag, tag_id)
    if not tag:
        raise HTTPException(status_code=404, detail="Тег не найден")
    session.delete(tag)
    session.commit()
