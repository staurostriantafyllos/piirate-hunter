from collections.abc import Generator
from contextlib import contextmanager

import pika
import redis
from minio import Minio
from pika.adapters.blocking_connection import BlockingChannel

from app.config import MinioConfig, RabbitMQConfig, RedisConfig

rabbitmq_config = RabbitMQConfig()
redis_config = RedisConfig()
minio_config = MinioConfig()  # type:ignore


def redis_connection() -> redis.Redis:
    """Provide a Redis connection."""

    return redis.Redis(host=redis_config.HOST, port=redis_config.PORT)


def minio_connection() -> Minio:
    """Provide a MinIO connection."""

    minio_client = Minio(
        endpoint=minio_config.ENDPOINT,
        access_key=minio_config.ROOT_USER,
        secret_key=minio_config.ROOT_PASSWORD,
        secure=minio_config.SECURE,
    )
    return minio_client


def rabbitmq_channel() -> Generator[BlockingChannel, None, None]:
    """Provide a RabbitMQ channel."""
    connection_parameters = pika.ConnectionParameters(host=rabbitmq_config.HOST)

    with pika.BlockingConnection(connection_parameters) as connection:
        with connection.channel() as channel:
            yield channel


@contextmanager
def rabbitmq_channel_ctx() -> Generator[BlockingChannel, None, None]:
    """Provide a RabbitMQ channel using a context manager."""
    yield from rabbitmq_channel()
