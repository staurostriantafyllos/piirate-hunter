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


class DatabaseSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix='POSTGRES_')

    USERNAME: str
    PASSWORD: str
    HOST: str
    PORT: int
    DATABASE: str
    POOL_SIZE: int = 5
    MAX_OVERFLOW: int = 10
    POOL_RECYCLE: int = -1
    POOL_PRE_PING: bool = False
    POOL_USE_LIFO: bool = False
    ECHO: bool = False
