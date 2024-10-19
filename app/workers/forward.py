import json
import logging

import pika
from pika.adapters.blocking_connection import BlockingChannel
from pika.spec import Basic

from app.factories import rabbitmq_channel_ctx
from app.models.validation import Exchange, Queue
from app.utils import publish_to_exchange

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


class Forward:
    def __init__(self, channel: BlockingChannel):
        self.channel = channel

    def process_message(
        self,
        channel: BlockingChannel,
        properties: pika.BasicProperties,
        image_url: str,
        pii_terms: list,
    ):
        """
        Publish the received message to the OCR and PII filter exchanges.
        """
        # Publish image URL to the OCR exchange
        publish_to_exchange(
            channel=channel,
            correlation_id=properties.correlation_id,
            body=image_url,
            routing_key="image.ocr",
            exchange=Exchange.OCR.value,
        )

        # Publish PII terms to the PII filter exchange
        publish_to_exchange(
            channel=channel,
            correlation_id=properties.correlation_id,
            body=json.dumps(pii_terms),
            routing_key="filter.pii",
            exchange=Exchange.FILTER.value,
        )

        logger.info(
            f"""Published data for correlation id '{properties.correlation_id}'
            to filtering and OCR exchanges."""
        )

    def on_message_received(
        self,
        channel: BlockingChannel,
        method: Basic.Deliver,
        properties: pika.BasicProperties,
        body: bytes,
    ) -> None:
        """
        Callback function triggered when a message is received.
        """
        data = json.loads(body)
        image_url = data["image_url"]
        pii_terms = data["pii_terms"]

        # Process and publish the message
        self.process_message(channel, properties, image_url, pii_terms)

        # Acknowledge the message
        channel.basic_ack(delivery_tag=method.delivery_tag)

    def setup_exchanges_and_queues(self):
        """
        Declare necessary RabbitMQ exchanges and queues.
        """
        # Declare the forward exchange where combined image and PII terms are published
        self.channel.exchange_declare(
            exchange=Exchange.FORWARD.value,
            exchange_type="topic",
            durable=True,
        )

        # Declare a new queue for the new subscriber to consume messages
        self.channel.queue_declare(
            queue=Queue.FORWARD.value,
            durable=True,
        )

        self.channel.queue_bind(
            exchange=Exchange.FORWARD.value,
            queue=Queue.FORWARD.value,
            routing_key="input",
        )

        # Declare OCR and Filter exchanges
        self.channel.exchange_declare(
            exchange=Exchange.OCR.value,
            exchange_type="topic",
            durable=True,
        )
        self.channel.exchange_declare(
            exchange=Exchange.FILTER.value,
            exchange_type="topic",
            durable=True,
        )

    def start(self):
        """
        Start consuming messages from the forward queue.
        """
        self.setup_exchanges_and_queues()

        self.channel.basic_consume(
            queue=Queue.FORWARD.value,
            on_message_callback=self.on_message_received,
            auto_ack=False,
        )
        self.channel.start_consuming()


def main():
    # Start the forwarding with the RabbitMQ channel
    with rabbitmq_channel_ctx() as channel:
        processor = Forward(channel)
        processor.start()


if __name__ == "__main__":
    main()
