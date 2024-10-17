from uuid import UUID

from sqlmodel import Session

from app.models.database import Result


def read_result(session: Session, correlation_id: UUID) -> Result | None:
    return session.get(Result, correlation_id)
