from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy.engine import URL, Engine
from sqlmodel import Session, create_engine

from app.config import DatabaseSettings

config = DatabaseSettings()  # type: ignore

engine = None


def create_database_engine() -> Engine:
    """
    Create and configure a `SQLAlchemy` database engine for PostgreSQL.

    Create a `SQLAlchemy` engine for PostgreSQL using credentials and configuration
    options found in the environment. The environment configuration is loaded using the
    `DatabaseSettings` model.

    Returns:
        A configured `SQLAlchemy` engine for interacting with the PostgreSQL database.
    """
    connection_string = URL.create(
        "postgresql",
        username=config.USERNAME,
        password=config.PASSWORD,
        host=config.HOST,
        database=config.DATABASE,
        port=config.PORT,
    )

    connect_args = {}

    engine = create_engine(
        connection_string,
        connect_args=connect_args,
        pool_size=config.POOL_SIZE,
        max_overflow=config.MAX_OVERFLOW,
        pool_recycle=config.POOL_RECYCLE,
        pool_pre_ping=config.POOL_PRE_PING,
        pool_use_lifo=config.POOL_USE_LIFO,
        echo=config.ECHO,
    )
    return engine


def get_db_session() -> Generator[Session, None, None]:
    """
    Provide a database session.

    Check if a `SQLAlchemy` engine exists and create it if necessary. Yield a new
    database session and handle committing the session after use and roll back in case
    of any exceptions.

    Yields:
        A `SQLModel` session object for interacting with the database.

    Raises:
        Any exception raised during the session operation, including but not limited to
        database connection errors, query execution errors, or transaction errors.
    """
    global engine
    if not engine:
        engine = create_database_engine()

    session = Session(engine)
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()  # Rollback in case of an error
        raise
    finally:
        session.close()


@contextmanager
def get_session_ctx() -> Generator[Session, None, None]:
    """
    Context manager for obtaining a database session.

    Yield a database session within a context manager, allowing for easy integration of
    session management in a `with` statement, ensuring that the session is properly
    handled.

    Yields:
        A `SQLModel` session object for interacting with the database.

    Usage:
        Use this context manager to automatically manage the session lifecycle:

        ```python
        with get_session_ctx() as session:
            # Perform database operations
        ```
    """
    yield from get_db_session()
