from enum import Enum

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


class SubmitResponse(SQLModel):
    correlation_id: str


class Exchange(Enum):
    FORWARD = "forward_exchange"
    OCR = "ocr_exchange"
    FILTER = "filter_exchange"


class Queue(Enum):
    FORWARD = "forward_queue"
    OCR = "ocr_queue"
    FILTER = "filter_queue"
