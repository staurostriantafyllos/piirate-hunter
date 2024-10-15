import os
import uuid
from io import BytesIO

import pika
from minio import Minio

from app.factories import rabbitmq_channel


def upload_object_to_minio(
    client: Minio,
    endpoint: str,
    bucket: str,
    path: str,
    filename: str,
    obj: BytesIO,
    content_type: str,
):
    """Upload an object to MinIO and return the url."""
    client.put_object(
        bucket_name=bucket,
        object_name=os.path.join(path, filename),
        data=obj,
        content_type=content_type,
        length=len(obj.getvalue()),
    )
    return os.path.join("http://", endpoint, bucket, path, filename)
    # return url


def publish_to_exchange(
    request_id: uuid.UUID | str,
    routing_key: str,
    body: str | bytes,
    exchange: str = "",
):
    """Publish a message to a RabbitMQ queue."""
    with rabbitmq_channel() as channel:
        channel.queue_declare(queue=routing_key, durable=True)

        properties = pika.BasicProperties(
            delivery_mode=2, correlation_id=str(request_id)
        )

        channel.basic_publish(
            exchange=exchange,
            routing_key=routing_key,
            body=body,
            properties=properties,
        )
