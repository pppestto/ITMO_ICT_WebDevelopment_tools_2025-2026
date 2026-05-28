from fastapi import APIRouter, HTTPException
from sqlmodel import select

from app.core.deps import CurrentUserDep, SessionDep
from app.models.category import Category
from app.schemas.category import CategoryCreate, CategoryRead, CategoryUpdate

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("/", response_model=list[CategoryRead])
def list_categories(session: SessionDep, current_user: CurrentUserDep) -> list[Category]:
    return list(session.exec(select(Category)).all())


@router.get("/{category_id}", response_model=CategoryRead)
def get_category(category_id: int, session: SessionDep, current_user: CurrentUserDep) -> Category:
    category = session.get(Category, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Категория не найдена")
    return category


@router.post("/", response_model=CategoryRead, status_code=201)
def create_category(
    payload: CategoryCreate, session: SessionDep, current_user: CurrentUserDep
) -> Category:
    category = Category(**payload.model_dump())
    session.add(category)
    session.commit()
    session.refresh(category)
    return category


@router.patch("/{category_id}", response_model=CategoryRead)
def update_category(
    category_id: int,
    payload: CategoryUpdate,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> Category:
    category = session.get(Category, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Категория не найдена")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(category, key, value)
    session.add(category)
    session.commit()
    session.refresh(category)
    return category


@router.delete("/{category_id}", status_code=204)
def delete_category(
    category_id: int, session: SessionDep, current_user: CurrentUserDep
) -> None:
    category = session.get(Category, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Категория не найдена")
    session.delete(category)
    session.commit()
