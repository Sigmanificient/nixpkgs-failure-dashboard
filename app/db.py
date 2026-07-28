from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .config import RUNTIME_DIR
from .models import Base

DATABASE_URL = f"sqlite:///{RUNTIME_DIR}/builds.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    Base.metadata.create_all(bind=engine)
