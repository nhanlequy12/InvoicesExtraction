from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from src.core.config import settings

# In SQLite fallback for local testing without active Postgres
DATABASE_URL = settings.SQLALCHEMY_DATABASE_URI
if "sqlite" in settings.POSTGRES_SERVER.lower() or settings.APP_ENV == "test":
    engine = create_engine("sqlite:///./data/test.db", connect_args={"check_same_thread": False})
else:
    # Use standard engine (connect_args can be customized for Postgres pool)
    try:
        engine = create_engine(
            DATABASE_URL,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20
        )
    except Exception:
        # Fallback to sqlite if postgres is not yet running locally
        engine = create_engine("sqlite:///./data/smart_invoice_dev.db", connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """Dependency for providing transactional database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
