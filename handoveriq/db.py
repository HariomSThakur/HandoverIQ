from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from flask import Flask
from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from .models import Base


def init_database(app: Flask) -> None:
    database_url = app.config["DATABASE_URL"]
    if database_url.startswith("sqlite:///"):
        db_path = database_url.removeprefix("sqlite:///")
        if db_path != ":memory:":
            Path(db_path).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    engine = create_engine(database_url, future=True, connect_args=connect_args)

    if database_url.startswith("sqlite"):
        @event.listens_for(engine, "connect")
        def enable_sqlite_foreign_keys(dbapi_connection, _connection_record) -> None:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    Base.metadata.create_all(engine)
    app.extensions["handoveriq_engine"] = engine
    app.extensions["handoveriq_session_factory"] = sessionmaker(
        bind=engine, expire_on_commit=False, class_=Session
    )


@contextmanager
def session_scope(app: Flask) -> Iterator[Session]:
    factory = app.extensions["handoveriq_session_factory"]
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_engine(app: Flask) -> Engine:
    return app.extensions["handoveriq_engine"]
