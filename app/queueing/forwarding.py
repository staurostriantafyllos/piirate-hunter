import json

import pika
from pika.channel import Channel
from pika.spec import Basic

from app.factories import rabbitmq_channel
from app.utils import publish_to_exchange


def on_message_received(
    ch: Channel, method: Basic.Deliver, properties: pika.BasicProperties, body: bytes
) -> None:
    data = json.loads(body)

    publish_to_exchange(
        request_id=properties.correlation_id,
        routing_key="ocr",
        body=data["image_url"],
    )

    publish_to_exchange(
        request_id=properties.correlation_id,
        routing_key="filtering-terms",
        body=json.dumps(data["pii_terms"]),
    )
    ch.basic_ack(method.delivery_tag)


with rabbitmq_channel() as channel:
    channel.queue_declare(queue="forwarding", durable=True)
    channel.basic_consume(queue="forwarding", on_message_callback=on_message_received)
    channel.start_consuming()
