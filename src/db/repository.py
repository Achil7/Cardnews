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
    "ALTER TABLE posts ADD COLUMN content_type VARCHAR DEFAULT 'news'",
    "ALTER TABLE posts ADD COLUMN demographic VARCHAR",
    "ALTER TABLE posts ADD COLUMN research_topic TEXT",
]

_POSTS_REBUILD_SQL = [
    """CREATE TABLE IF NOT EXISTS posts_new (
        id INTEGER PRIMARY KEY,
        article_id INTEGER REFERENCES articles(id),
        account_handle VARCHAR,
        content_type VARCHAR DEFAULT 'news',
        demographic VARCHAR,
        research_topic TEXT,
        slides_json TEXT,
        caption TEXT,
        hashtags TEXT,
        output_dir VARCHAR,
        created_at DATETIME,
        published_at DATETIME,
        status VARCHAR DEFAULT 'pending',
        error_log TEXT
    )""",
    "INSERT OR IGNORE INTO posts_new SELECT id, article_id, account_handle, content_type, demographic, research_topic, slides_json, caption, hashtags, output_dir, created_at, published_at, status, error_log FROM posts",
    "DROP TABLE posts",
    "ALTER TABLE posts_new RENAME TO posts",
]


def _run_migrations():
    with engine.connect() as conn:
        for sql in _MIGRATIONS:
            try:
                conn.execute(text(sql))
                conn.commit()
            except Exception:
                conn.rollback()

        try:
            row = conn.execute(text(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name='posts'"
            )).fetchone()
            if row and "NOT NULL" in row[0] and "article_id" in row[0]:
                for sql in _POSTS_REBUILD_SQL:
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
