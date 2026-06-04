from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from config import PROJECT_ROOT, settings
from .models import Base

engine = create_engine(settings.database_url, echo=False, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

_MIGRATIONS = [
    "ALTER TABLE articles ADD COLUMN region VARCHAR DEFAULT 'korean'",
    "ALTER TABLE posts ADD COLUMN account_handle VARCHAR",
]


def _run_migrations():
    with engine.connect() as conn:
        for sql in _MIGRATIONS:
            try:
                conn.execute(text(sql))
                conn.commit()
            except Exception:
                conn.rollback()


def init_db():
    data_dir = PROJECT_ROOT / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(engine)
    _run_migrations()


@contextmanager
def db_session() -> Session:
    s = SessionLocal()
    try:
        yield s
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()
