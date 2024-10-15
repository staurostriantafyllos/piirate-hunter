import json
from io import BytesIO

import pika
import pytesseract
import requests
from pika.channel import Channel
from pika.spec import Basic
from PIL import Image
from spacy.lang.en import English

from app.factories import rabbitmq_channel
from app.models.validation import TextBoundingBox
from app.utils import publish_to_exchange

nlp = English()


def preprocess_text(text: str) -> str:
    """Remove punctuation from a string using spaCy."""
    doc = nlp(text)
    clean_tokens = [token.text for token in doc if not token.is_punct]

    return " ".join(clean_tokens)


def detect_text(image_data: BytesIO) -> list[TextBoundingBox]:
    """Extract text from an image."""
    image = Image.open(image_data)

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
    ch: Channel, method: Basic.Deliver, properties: pika.BasicProperties, body: bytes
) -> None:
    image_url = body.decode()

    response = requests.get(image_url)
    image = BytesIO(response.content)

    results = detect_text(image)

    results = [b.model_dump() for b in results]

    publish_to_exchange(
        request_id=properties.correlation_id,
        routing_key="filtering-ocr",
        body=json.dumps(results),
    )
    ch.basic_ack(method.delivery_tag)


with rabbitmq_channel() as channel:
    channel.queue_declare(queue="ocr", durable=True)
    channel.basic_consume(queue="ocr", on_message_callback=on_message_received)
    channel.start_consuming()
