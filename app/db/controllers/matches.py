from uuid import UUID

from sqlmodel import Session

from app.models.database import Matches


def read_match(session: Session, correlation_id: UUID) -> Matches | None:
    return session.get(Matches, correlation_id)


def write_matches(session: Session, correlation_id: UUID, terms: list[dict]) -> Matches:
    match = Matches(
        correlation_id=correlation_id,
        terms=terms,
    )
    session.add(match)

    return match
