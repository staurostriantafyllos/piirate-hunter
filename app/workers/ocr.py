import json
import logging
from io import BytesIO

import pika
import requests
from pika.adapters.blocking_connection import BlockingChannel
from pika.spec import Basic

from app.factories import rabbitmq_channel_ctx
from app.utils import detect_text, publish_to_exchange
from app.models.validation import Exchange, Queue

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)


class OCR:
    def __init__(self, channel: BlockingChannel):
        self.channel = channel

    def process_message(
        self,
        channel: BlockingChannel,
        correlation_id: str,
        image_url: str,
    ):
        """
        Download the image from the provided URL, process it using OCR, and publish the results.
        """
        # Download the image from the URL
        response = requests.get(image_url)
        image_file = BytesIO(response.content)

        # Process the image with OCR
        results = detect_text(image_file)

        # Convert the OCR results into a list of dictionaries
        results = [b.model_dump() for b in results]

        # Publish OCR results to the filter exchange
        publish_to_exchange(
            channel=channel,
            correlation_id=correlation_id,
            body=json.dumps(results),
            routing_key='filter.ocr',
            exchange=Exchange.FILTER.value,
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
        image_url = body.decode()  # Decode the message to get the image URL

        # Process and publish the message
        self.process_message(channel, properties.correlation_id, image_url)

        # Acknowledge the message
        channel.basic_ack(delivery_tag=method.delivery_tag)

        logger.info(
            f"Published OCR results for correlation id '{properties.correlation_id}' to filtering exchange."
        )

    def setup_exchanges_and_queues(self):
        """
        Declare necessary RabbitMQ exchanges and queues.
        """
        # Declare Incoming Exchanges & Queues
        self.channel.exchange_declare(
            exchange=Exchange.OCR.value,
            exchange_type="topic",
            durable=True,
        )

        self.channel.queue_declare(
            queue=Queue.OCR.value,
            durable=True,
        )

        self.channel.queue_bind(
            exchange=Exchange.OCR.value,
            queue=Queue.OCR.value,
            routing_key="image.ocr",
        )

        # Declare Outgoing Exchanges
        self.channel.exchange_declare(
            exchange=Exchange.FILTER.value,
            exchange_type="topic",
            durable=True,
        )

    def start(self):
        """
        Start consuming messages from the OCR queue.
        """
        self.setup_exchanges_and_queues()

        self.channel.basic_consume(
            queue=Queue.OCR.value,
            on_message_callback=self.on_message_received,
            auto_ack=False,
        )
        self.channel.start_consuming()


def main():
    # Start the OCR processor with the RabbitMQ channel
    with rabbitmq_channel_ctx() as channel:
        processor = OCR(channel)
        processor.start()


if __name__ == "__main__":
    main()
