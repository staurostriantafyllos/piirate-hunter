from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routers.pii import pii_router
from app.config import APISettings
from app.factories import rabbitmq_channel_ctx
from app.models.validation import Exchange

config = APISettings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    with rabbitmq_channel_ctx() as channel:
        channel.exchange_declare(
            exchange=Exchange.FORWARD.value, exchange_type="topic", durable=True
        )
    yield


app = FastAPI(
    lifespan=lifespan,
    title=config.TITLE,
    description=config.DESCRIPTION,
    version=config.VERSION,
)
app.include_router(pii_router)
