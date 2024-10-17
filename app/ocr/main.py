import json
from io import BytesIO

import pika
import pytesseract
import requests
from pika.channel import Channel
from pika.spec import Basic
from PIL import Image
import spacy

from app.factories import rabbitmq_channel_ctx
from app.models.validation import TextBoundingBox
from app.utils import publish_to_exchange


nlp = spacy.blank("xx")


def preprocess_text(text: str) -> str:
    """Remove punctuation from a string using spaCy."""
    doc = nlp(text)
    clean_tokens = [
        token.text for token in doc if not (token.is_punct or token.is_space)
    ]
    return " ".join(clean_tokens)


def detect_text(image_file: BytesIO) -> list[TextBoundingBox]:
    """Extract text from an image."""
    image = Image.open(image_file)

    data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)

    result = []
    n_boxes = len(data["level"])
    for i in range(n_boxes):
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


def on_message_received(
    channel: Channel,
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
