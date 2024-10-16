import json
import uuid
from io import BytesIO

from fastapi import Depends, FastAPI, File, HTTPException, Query, UploadFile, status
from minio import Minio
from sqlmodel import Session

from app.config import MinioConfig
from app.db.controllers import results
from app.db.factories import get_db_session
from app.factories import minio_connection, redis_connection
from app.models.validation import TextBoundingBox
from app.utils import publish_to_exchange, upload_object_to_minio

minio_config = MinioConfig()  # type:ignore
app = FastAPI()


@app.post("/")
async def submit(
    image: UploadFile = File(),
    pii_terms: list[str] = Query(),
    conn: Minio = Depends(minio_connection),
):
    request_id = uuid.uuid4()

    imgb = BytesIO(image.file.read())
    image_url = upload_object_to_minio(
        client=conn,
        endpoint=minio_config.ENDPOINT,
        bucket=minio_config.BUCKET,
        path=minio_config.PATH,
        filename=f"{request_id}_{image.filename}",
        obj=imgb,
        content_type=image.content_type,
    )

    data = {"image_url": image_url, "pii_terms": pii_terms}

    publish_to_exchange(
        request_id=request_id,
        routing_key="forwarding",
        body=json.dumps(data),
    )

    return {"request_id": request_id}


@app.get("/", response_model=list[TextBoundingBox])
async def read_result(
    request_id: uuid.UUID, session: Session = Depends(get_db_session)
):
    data = results.read_result(session=session, request_id=request_id)

    if not data:
        raise HTTPException(status.HTTP_404_NOT_FOUND)

    return data.matches
