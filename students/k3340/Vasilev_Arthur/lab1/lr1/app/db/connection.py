import os

from dotenv import load_dotenv
from sqlmodel import Session, create_engine

load_dotenv()

db_url = os.getenv("DB_ADMIN", "postgresql://postgres:123@localhost/time_manager_db")

engine = create_engine(db_url, echo=False)


def get_session() -> Session:
    with Session(engine) as session:
        yield session
