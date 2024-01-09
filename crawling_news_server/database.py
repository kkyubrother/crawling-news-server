import os
from contextlib import contextmanager
from dotenv import load_dotenv

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

load_dotenv()

SQLALCHEMY_DATABASE_URL = os.environ.get("DB_PATH")

connect_args = {}
if "sqlite" in SQLALCHEMY_DATABASE_URL.split("//")[0]:
    connect_args['check_same_thread'] = False

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args=connect_args,
    pool_size=100
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_context_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()