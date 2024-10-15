from pydantic_settings import BaseSettings, SettingsConfigDict


class MinioConfig(BaseSettings):
    """
    Configuration model for MinIO.

    Variables will be loaded from the environment.
    """

    model_config = SettingsConfigDict(env_prefix="MINIO_")

    ENDPOINT: str = "localhost:9000"
    ROOT_USER: str
    ROOT_PASSWORD: str
    SECURE: bool = True
    BUCKET: str
    PATH: str


class RedisConfig(BaseSettings):
    """
    Configuration model for Redis.

    Variables will be loaded from the environment.
    """

    model_config = SettingsConfigDict(env_prefix="REDIS_")

    HOST: str = "localhost"
    PORT: int = 6379


class RabbitMQConfig(BaseSettings):
    """
    Configuration model for RabbitMQ.

    Variables will be loaded from the environment.
    """

    model_config = SettingsConfigDict(env_prefix="RABBITMQ_")

    HOST: str = "localhost"
