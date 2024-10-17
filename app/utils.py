import os
from io import BytesIO

import pika
from pika.channel import Channel
from minio import Minio


def upload_object_to_minio(
    client: Minio,
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

    base_url = client._base_url._url.geturl()
    return os.path.join(base_url, bucket, path, filename)


def publish_to_exchange(
    channel: Channel,
    correlation_id: str | None,
    body: str | bytes,
    routing_key: str,
    exchange: str = "",
):
    """Publish a message to a RabbitMQ queue."""
    properties = pika.BasicProperties(
        delivery_mode=2,
        correlation_id=correlation_id,
    )

    channel.basic_publish(
        exchange=exchange,
        routing_key=routing_key,
        body=body,
        properties=properties,
    )
