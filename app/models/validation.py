from pydantic import BaseModel
from sqlmodel import SQLModel


class TextBoundingBox(BaseModel):
    """
    Pillow-type Bounding Box.
    Coordinates start in (0,0) in the Top Left Corner.
    """

    text: str
    left: int
    right: int
    top: int
    bottom: int


class ResultResponse(SQLModel):
    matches: list[TextBoundingBox]
