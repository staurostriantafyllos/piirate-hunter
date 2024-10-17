import json
import logging
from uuid import UUID

import pika
from pika.channel import Channel
from pika.spec import Basic

from app.db.controllers.results import write_result
from app.db.factories import get_session_ctx
from app.factories import rabbitmq_channel_ctx, redis_connection
from app.models.validation import TextBoundingBox
from app.utils import find_matches

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

logger = logging.getLogger(__name__)


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
        bounding_boxes = [
            TextBoundingBox.model_validate(box) for box in json.loads(ocr_result)
        ]
        pii_terms = json.loads(pii_terms)

        matches = find_matches(
            bounding_boxes=bounding_boxes,
            pii_terms=pii_terms,
        )

        with get_session_ctx() as session:
            write_result(
                session=session,
                correlation_id=UUID(correlation_id),
                matches=matches,
            )

        r.delete(pii_terms_key)
        r.delete(ocr_key)

        logger.info(f"Processed item {correlation_id}. Matches: {len(matches)}")
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
