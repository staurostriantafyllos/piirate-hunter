from datetime import datetime
from uuid import UUID

from sqlmodel import JSON, Column, Field, SQLModel, func


class Result(SQLModel, table=True):
    __tablename__ = "results"  # type: ignore

    request_id: UUID = Field(primary_key=True)
    matches: list = Field(sa_column=Column(JSON))
    created_at: datetime = Field(
        default=None, sa_column_kwargs={"server_default": func.now()}
    )
