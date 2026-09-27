"""SQLAlchemy 引擎与会话。pool_pre_ping + pool_recycle 是生产要点：
MySQL wait_timeout 断连后连接池里的死连接会被自动剔除重连。"""
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import settings

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600,
    pool_size=5,
    max_overflow=5,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
