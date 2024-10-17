import json

import pika
from pika.channel import Channel
from pika.spec import Basic

from app.factories import rabbitmq_channel_ctx
from app.utils import publish_to_exchange


def on_message_received(
    channel: Channel,
    method: Basic.Deliver,
    properties: pika.BasicProperties,
    body: bytes,
) -> None:
    data = json.loads(body)

    image_url = data['image_url']
    pii_terms = data['pii_terms']

    publish_to_exchange(
        channel=channel,
        correlation_id=properties.correlation_id,
        body=image_url,
        routing_key='image.process.ocr',
        exchange="ocr_exchange",
    )

    publish_to_exchange(
        channel=channel,
        correlation_id=properties.correlation_id,
        body=json.dumps(pii_terms),
        routing_key='filter.pii',
        exchange="filter_exchange",
    )
    channel.basic_ack(delivery_tag=method.delivery_tag)


with rabbitmq_channel_ctx() as channel:

    # Declare the input exchange where combined image and PII terms are published
    channel.exchange_declare(
        exchange="input_exchange",
        exchange_type="topic",
        durable=True,
    )

    # Declare a new queue for the new subscriber to consume messages
    channel.queue_declare(
        queue="input_queue",
        durable=True,
    )
    channel.queue_bind(
        exchange="input_exchange",
        queue="input_queue",
        routing_key="input.data",
    )

    # Declare OCR and Filter exchanges
    channel.exchange_declare(
        exchange="ocr_exchange",
        exchange_type="topic",
        durable=True,
    )
    channel.exchange_declare(
        exchange="filter_exchange",
        exchange_type="topic",
        durable=True,
    )

    # Listen for messages
    channel.basic_consume(
        queue="input_queue",
        on_message_callback=on_message_received,
        auto_ack=False,
    )
    channel.start_consuming()
