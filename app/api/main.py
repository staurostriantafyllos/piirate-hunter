import json
import uuid
from contextlib import asynccontextmanager
from io import BytesIO

from fastapi import Depends, FastAPI, File, HTTPException, Query, UploadFile, status
from minio import Minio
from pika.adapters.blocking_connection import BlockingChannel
from sqlmodel import Session

from app.config import MinioConfig
from app.db.controllers import results
from app.db.factories import get_db_session
from app.factories import minio_connection, rabbitmq_channel, rabbitmq_channel_ctx
from app.models.validation import ResultResponse, SubmitResponse
from app.utils import publish_to_exchange, upload_object_to_minio

minio_config = MinioConfig()  # type:ignore


@asynccontextmanager
async def lifespan(app: FastAPI):
    with rabbitmq_channel_ctx() as channel:
        channel.exchange_declare(
            exchange="input_exchange", exchange_type="topic", durable=True
        )
    yield


app = FastAPI(lifespan=lifespan)


@app.post("/pii")
async def submit(
    image: UploadFile = File(),
    pii_terms: list[str] = Query(),
    minio_client: Minio = Depends(minio_connection),
    rabbitmq_channel: BlockingChannel = Depends(rabbitmq_channel),
) -> SubmitResponse:
    correlation_id = str(uuid.uuid4())
    image_file = BytesIO(image.file.read())

    image_url = upload_object_to_minio(
        client=minio_client,
        bucket=minio_config.BUCKET,
        path=minio_config.PATH,
        filename=f"{correlation_id}_{image.filename}",
        obj=image_file,
        content_type=image.content_type,
    )

    publish_to_exchange(
        channel=rabbitmq_channel,
        correlation_id=correlation_id,
        body=json.dumps(
            {
                "image_url": image_url,
                "pii_terms": pii_terms,
            }
        ),
        routing_key='input.data',
        exchange="input_exchange",
    )
    return SubmitResponse(correlation_id=correlation_id)


@app.get("/pii/{correlation_id}")
async def read_result(
    correlation_id: uuid.UUID, session: Session = Depends(get_db_session)
) -> ResultResponse:
    data = results.read_result(session=session, correlation_id=correlation_id)

    if not data:
        raise HTTPException(status.HTTP_404_NOT_FOUND)

    return ResultResponse(matches=data.matches)
