from datetime import datetime
from uuid import UUID

from sqlmodel import JSON, Column, Field, SQLModel, func


class Matches(SQLModel, table=True):
    __tablename__ = "matches"  # type: ignore

    correlation_id: UUID = Field(primary_key=True)
    terms: list = Field(sa_column=Column(JSON))
    created_at: datetime = Field(
        default=None, sa_column_kwargs={"server_default": func.now()}
    )
