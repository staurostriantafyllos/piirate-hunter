import json
import uuid
from io import BytesIO

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from minio import Minio
from pika.adapters.blocking_connection import BlockingChannel
from sqlmodel import Session

from app.config import MinioConfig
from app.db.controllers import matches
from app.db.factories import get_db_session
from app.factories import minio_connection, rabbitmq_channel
from app.models.validation import Exchange, MatchResponse, SubmitResponse
from app.utils import publish_to_exchange, upload_object_to_minio

minio_config = MinioConfig()  # type:ignore


pii_router = APIRouter(
    prefix="/pii",
    tags=["PII"],
)


@pii_router.post("")
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
        routing_key="input",
        exchange=Exchange.FORWARD.value,
    )
    return SubmitResponse(correlation_id=correlation_id)


@pii_router.get("/{correlation_id}")
async def read_result(
    correlation_id: uuid.UUID, session: Session = Depends(get_db_session)
) -> MatchResponse:
    data = matches.read_match(session=session, correlation_id=correlation_id)

    if not data:
        raise HTTPException(status.HTTP_404_NOT_FOUND)

    return MatchResponse(matches=data.terms)
