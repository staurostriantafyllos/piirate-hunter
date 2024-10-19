import json
import logging
from uuid import UUID

import pika
from pika.adapters.blocking_connection import BlockingChannel
from pika.spec import Basic

from app.db.controllers.matches import write_matches
from app.db.factories import get_session_ctx
from app.factories import rabbitmq_channel_ctx, redis_connection
from app.models.validation import Exchange, Queue, TextBoundingBox
from app.utils import find_matches

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


class Filter:
    def __init__(self, channel: BlockingChannel):
        self.channel = channel

    def process_results_and_store_matches(
        self, correlation_id: str, ocr_result: bytes, pii_terms: bytes
    ):
        """
        Process the OCR results and PII terms, find matches, and store them
        in the database.
        """
        # Deserialize the OCR results and PII terms
        bounding_boxes = [
            TextBoundingBox.model_validate(box) for box in json.loads(ocr_result)
        ]
        pii_terms_dict = json.loads(pii_terms)

        # Find matches between bounding boxes and PII terms
        matched_terms = find_matches(
            bounding_boxes=bounding_boxes,
            pii_terms=pii_terms_dict,
        )

        # Store matches in the database
        with get_session_ctx() as session:
            result = write_matches(
                session=session,
                correlation_id=UUID(correlation_id),
                terms=matched_terms,
            )
            logger.info(
                f"Processed item {result.correlation_id}. Matches: {len(matched_terms)}"
            )

    def process_message(self, body: bytes, method: Basic.Deliver, correlation_id: str):
        """
        Process the message by storing it in Redis and retrieving data to find matches.
        """
        with redis_connection() as redis_conn:
            # Generate keys based on the correlation ID
            ocr_key = f"{correlation_id}:ocr"
            pii_terms_key = f"{correlation_id}:pii_terms"

            this_key = None
            if method.routing_key == "filter.pii":
                this_key = pii_terms_key
            elif method.routing_key == "filter.ocr":
                this_key = ocr_key

            # Store the message in Redis only if the key doesn't exist
            if not redis_conn.exists(this_key):
                redis_conn.set(this_key, body)
                logger.info(f"Stored data for key: {this_key}")

            # Retrieve OCR result and PII terms from Redis
            ocr_result = redis_conn.get(ocr_key)
            pii_terms = redis_conn.get(pii_terms_key)

            if ocr_result and pii_terms:
                # Process the results and store matches in the database
                self.process_results_and_store_matches(
                    correlation_id, ocr_result, pii_terms
                )

                # Clean up Redis keys after processing
                redis_conn.delete(pii_terms_key)
                redis_conn.delete(ocr_key)

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
        correlation_id = properties.correlation_id

        self.process_message(body, method, correlation_id)

        channel.basic_ack(method.delivery_tag)

    def setup_queues_and_exchanges(self):
        """
        Declare necessary RabbitMQ exchanges and queues.
        """
        self.channel.exchange_declare(
            exchange=Exchange.FILTER.value, exchange_type="topic", durable=True
        )

        self.channel.queue_declare(queue=Queue.FILTER.value, durable=True)

        self.channel.queue_bind(
            exchange=Exchange.FILTER.value,
            queue=Queue.FILTER.value,
            routing_key="filter.pii",
        )

        self.channel.queue_bind(
            exchange=Exchange.FILTER.value,
            queue=Queue.FILTER.value,
            routing_key="filter.ocr",
        )

    def start(self):
        """
        Start consuming messages from RabbitMQ.
        """
        self.setup_queues_and_exchanges()

        self.channel.basic_consume(
            queue=Queue.FILTER.value,
            on_message_callback=self.on_message_received,
            auto_ack=False,
        )
        self.channel.start_consuming()


def main():
    # Start the filtering with the RabbitMQ channel
    with rabbitmq_channel_ctx() as channel:
        processor = Filter(channel)
        processor.start()


if __name__ == "__main__":
    main()
