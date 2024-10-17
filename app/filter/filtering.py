import json
from uuid import UUID

import pika
from pika.channel import Channel
from pika.spec import Basic

from app.db.factories import get_session_ctx
from app.factories import rabbitmq_channel_ctx, redis_connection
from app.models.database import Result
from app.models.validation import TextBoundingBox


def filter_to_pii(
    bounding_boxes: list[TextBoundingBox], pii_terms: list[str]
) -> list[TextBoundingBox]:
    # this performs an exact match for now
    matches = []
    for box in bounding_boxes:
        if box.text not in pii_terms:
            matches.append(box)
    return matches


def find_matches(correlation_id: str, bounding_boxes: list, pii_terms: list):
    bounding_boxes = [TextBoundingBox.model_validate(box) for box in bounding_boxes]
    matches = filter_to_pii(bounding_boxes, pii_terms)
    matches = [m.model_dump() for m in matches]
    with get_session_ctx() as session:
        result = Result(
            correlation_id=UUID(correlation_id),
            matches=matches,
        )
        session.add(result)


def on_message_received(
    channel: Channel,
    method: Basic.Deliver,
    properties: pika.BasicProperties,
    body: bytes,
) -> None:
    correlation_id = properties.correlation_id

    ocr_key = f"{correlation_id}:ocr"
    pii_terms_key = f"{correlation_id}:pii_terms"

    this_key = None

    if method.routing_key == "filter.pii":
        this_key = pii_terms_key
    elif method.routing_key == "filter.boxes":
        this_key = ocr_key

    with redis_connection() as r:
        if not r.exists(this_key):
            r.set(this_key, body)

        ocr_result = r.get(ocr_key)
        pii_terms = r.get(pii_terms_key)

    if ocr_result and pii_terms:
        find_matches(
            correlation_id=correlation_id,
            bounding_boxes=json.loads(ocr_result),
            pii_terms=json.loads(pii_terms),
        )
        r.delete(pii_terms_key)
        r.delete(ocr_key)
    channel.basic_ack(method.delivery_tag)


with rabbitmq_channel_ctx() as channel:

    # Declare Incoming Exchanges & Queues
    channel.exchange_declare(
        exchange='filter_exchange', exchange_type='topic', durable=True
    )

    channel.queue_declare(queue='filter_queue', durable=True)
    channel.queue_bind(
        exchange='filter_exchange', queue='filter_queue', routing_key='filter.pii'
    )
    channel.queue_bind(
        exchange='filter_exchange', queue='filter_queue', routing_key='filter.boxes'
    )

    channel.basic_consume(
        queue='filter_queue', on_message_callback=on_message_received, auto_ack=False
    )

    channel.start_consuming()
