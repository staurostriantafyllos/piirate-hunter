import json
import logging
from io import BytesIO

import pika
import requests
from pika.adapters.blocking_connection import BlockingChannel
from pika.spec import Basic

from app.factories import rabbitmq_channel_ctx
from app.utils import detect_text, publish_to_exchange

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

logger = logging.getLogger(__name__)


def on_message_received(
    channel: BlockingChannel,
    method: Basic.Deliver,
    properties: pika.BasicProperties,
    body: bytes,
) -> None:
    image_url = body.decode()

    response = requests.get(image_url)
    image_file = BytesIO(response.content)

    results = detect_text(image_file)

    results = [b.model_dump() for b in results]

    publish_to_exchange(
        channel=channel,
        correlation_id=properties.correlation_id,
        body=json.dumps(results),
        routing_key='filter.boxes',
        exchange="filter_exchange",
    )
    channel.basic_ack(delivery_tag=method.delivery_tag)
    logger.info(
        f"Published OCR results for correlation id '{properties.correlation_id}' to filtering exchange."
    )


with rabbitmq_channel_ctx() as channel:

    # Declare Incoming Exchanges & Queues
    channel.exchange_declare(
        exchange='ocr_exchange',
        exchange_type='topic',
        durable=True,
    )
    channel.queue_declare(queue='ocr_queue', durable=True)
    channel.queue_bind(
        exchange='ocr_exchange',
        queue='ocr_queue',
        routing_key='image.process.ocr',
    )
    # Declare Outgoing Exchanges
    channel.exchange_declare(
        exchange='filter_exchange',
        exchange_type='topic',
        durable=True,
    )

    # Listen for messages
    channel.basic_consume(
        queue='ocr_queue',
        on_message_callback=on_message_received,
        auto_ack=False,
    )
    channel.start_consuming()
