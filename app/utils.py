import os
from io import BytesIO

import pika
import pytesseract
import spacy
from minio import Minio
from pika.adapters.blocking_connection import BlockingChannel
from PIL import Image

from app.models.validation import TextBoundingBox

nlp = spacy.blank("xx")


def upload_object_to_minio(
    client: Minio,
    bucket: str,
    path: str,
    filename: str,
    obj: BytesIO,
    content_type: str,
) -> str:
    """Upload an object to MinIO and return the url."""
    client.put_object(
        bucket_name=bucket,
        object_name=os.path.join(path, filename),
        data=obj,
        content_type=content_type,
        length=len(obj.getvalue()),
    )

    base_url = client._base_url._url.geturl()
    return os.path.join(base_url, bucket, path, filename)


def publish_to_exchange(
    channel: BlockingChannel,
    correlation_id: str | None,
    body: str | bytes,
    routing_key: str,
    exchange: str = "",
) -> None:
    """Publish a message to a RabbitMQ queue using an exchange."""
    properties = pika.BasicProperties(
        delivery_mode=2,
        correlation_id=correlation_id,
    )

    channel.basic_publish(
        exchange=exchange,
        routing_key=routing_key,
        body=body,
        properties=properties,
    )


def filter_to_pii(
    bounding_boxes: list[TextBoundingBox], pii_terms: list[str]
) -> list[TextBoundingBox]:
    """
    Filter to bounding boxes that contain personally identifiable information (PII).

    Take a list of `TextBoundingBox` objects and filter them based on whether their text
    matches any term in the provided list of PII terms.

    Args:
        bounding_boxes: A list of text bounding boxes to filter.
        pii_terms: A list of terms considered to be PII for matching.

    Returns:
        A list of bounding boxes whose text matches any of the PII terms.
    """
    # this performs an exact match for now
    matches = []
    for box in bounding_boxes:
        if box.text in pii_terms:
            matches.append(box)
    return matches


def find_matches(
    bounding_boxes: list[TextBoundingBox], pii_terms: list[str]
) -> list[dict]:
    """
    Find the bounding boxes that match any of the PII terms.

    Args:
        bounding_boxes: A list of text bounding boxes.
        pii_terms: A list of terms considered to be PII.

    Returns:
        A list of the dictionary representations of the bounding boxes that match the PII terms.
    """
    matches = filter_to_pii(bounding_boxes, pii_terms)
    return [m.model_dump() for m in matches]


def preprocess_text(text: str) -> str:
    """Remove punctuation from a string using spaCy."""
    doc = nlp(text)
    clean_tokens = [
        token.text for token in doc if not (token.is_punct or token.is_space)
    ]
    return " ".join(clean_tokens)


def detect_text(image_file: BytesIO) -> list[TextBoundingBox]:
    """
    Extract text from an image.

    Args:
        image_file: The target image.

    Returns:
        A list of bounding boxes with the detected text.
    """
    image = Image.open(image_file)

    data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)

    result = []
    for i in range(len(data["level"])):
        if data["conf"][i] == -1:
            continue

        result.append(
            TextBoundingBox(
                text=preprocess_text(data["text"][i]),
                left=data["left"][i],
                right=data["left"][i] + data["width"][i],
                top=data["top"][i],
                bottom=data["top"][i] + data["height"][i],
            )
        )

    return result
