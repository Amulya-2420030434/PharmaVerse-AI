from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings


connect_args = {}
if "psycopg" in settings.database_url:
    # Supabase uses transaction pooling on port 6543 (PgBouncer/Supavisor).
    # Prepared statements must be disabled in transaction pool mode to prevent
    # 'prepared statement does not exist' errors across pooled backend processes.
    connect_args["prepare_threshold"] = None

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_recycle=300,
    connect_args=connect_args,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False
)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()
