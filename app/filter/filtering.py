import json
from uuid import UUID

import pika
from pika.channel import Channel
from pika.spec import Basic

from app.db.factories import get_session_ctx
from app.factories import rabbitmq_channel, redis_connection
from app.models.database import Result
from app.models.validation import TextBoundingBox


def filter_to_pii(
    bounding_boxes: list[TextBoundingBox], pii_terms: list[str]
) -> list[TextBoundingBox]:
    # this performs an exact match for now
    matches = []
    for box in bounding_boxes:
        if box.text in pii_terms:
            matches.append(box)
    return matches


def find_matches(request_id: str, bounding_boxes: list, pii_terms: list):
    bounding_boxes = [TextBoundingBox.model_validate(b) for b in bounding_boxes]
    matches = filter_to_pii(bounding_boxes, pii_terms)
    matches = [m.model_dump() for m in matches]
    with get_session_ctx() as session:
        result = Result(request_id=UUID(request_id), matches=matches)
        session.add(result)


def on_message_received(
    ch: Channel, method: Basic.Deliver, properties: pika.BasicProperties, body: bytes
) -> None:
    request_id = properties.correlation_id

    if method.routing_key == "filtering-terms":
        with redis_connection() as conn:
            if not conn.exists(f"{request_id}:ocr"):
                conn.set(f"{request_id}:pii_terms", body)
            else:
                ocr_result = conn.get(f"{request_id}:ocr")
                find_matches(request_id, json.loads(ocr_result), json.loads(body))
    elif method.routing_key == "filtering-ocr":
        with redis_connection() as conn:
            if not conn.exists(f"{request_id}:pii_terms"):
                conn.set(f"{request_id}:ocr", body)
            else:
                pii_terms = json.loads(conn.get(f"{request_id}:pii_terms"))
                find_matches(request_id, json.loads(body), pii_terms)
    ch.basic_ack(method.delivery_tag)


with rabbitmq_channel() as channel:
    channel.queue_declare(queue="filtering-ocr", durable=True)
    channel.basic_consume(
        queue="filtering-ocr", on_message_callback=on_message_received
    )

    channel.queue_declare(queue="filtering-terms", durable=True)
    channel.basic_consume(
        queue="filtering-terms", on_message_callback=on_message_received
    )

    channel.start_consuming()
