from uuid import UUID

from sqlmodel import Session

from app.models.database import Result


def read_result(session: Session, correlation_id: UUID) -> Result | None:
    return session.get(Result, correlation_id)


def write_result(session: Session, correlation_id: UUID, matches: list[dict]) -> Result:
    result = Result(
        correlation_id=correlation_id,
        matches=matches,
    )
    session.add(result)

    return result
