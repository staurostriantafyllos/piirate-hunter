import logging

import alembic.config
from minio import Minio
from minio.error import S3Error

from app.config import MinioConfig
from app.factories import minio_connection


def create_bucket(client: Minio, bucket_name: str) -> None:
    """Create a bucket in MinIO."""
    try:
        if not client.bucket_exists(bucket_name):
            client.make_bucket(bucket_name)
            logger.info(f"Bucket '{bucket_name}' created.")
        else:
            logger.info(f"Bucket '{bucket_name}' already exists.")
    except S3Error:
        logger.exception(f"Failed to create bucket '{bucket_name}'.")


def set_public_read_access(client: Minio, bucket_name: str) -> None:
    """Set public read access for a bucket."""
    policy = f"""
    {{
        "Version": "2012-10-17",
        "Statement": [
            {{
                "Effect": "Allow",
                "Principal": "*",
                "Action": "s3:GetObject",
                "Resource": "arn:aws:s3:::{bucket_name}/*"
            }}
        ]
    }}
    """
    try:
        client.set_bucket_policy(bucket_name, policy)
        logger.info(f"Public read access set for bucket '{bucket_name}'.")
    except S3Error:
        logger.exception(
            f"Error setting public read access for bucket '{bucket_name}'."
        )


def setup_minio() -> None:
    minio_config = MinioConfig()  # type: ignore
    client = minio_connection()
    create_bucket(client=client, bucket_name=minio_config.BUCKET)
    set_public_read_access(client=client, bucket_name=minio_config.BUCKET)


def setup_postgres() -> None:
    alembic.config.main(
        [
            '--raiseerr',
            'upgrade',
            'head',
        ]
    )


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s'
    )

    logger = logging.getLogger(__name__)

    setup_minio()
    setup_postgres()
