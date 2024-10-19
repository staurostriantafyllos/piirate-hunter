import os
from io import BytesIO
from unittest.mock import MagicMock, Mock

from minio import Minio
from pika import BasicProperties

from app.models.validation import TextBoundingBox
from app.utils import (
    detect_text,
    filter_to_pii,
    preprocess_text,
    publish_to_exchange,
    upload_object_to_minio,
)


def test_filter_to_pii():
    bounding_boxes = [
        TextBoundingBox(text="one", left=0, right=1, top=0, bottom=1),
        TextBoundingBox(text="two", left=1, right=2, top=1, bottom=2),
        TextBoundingBox(text="three", left=2, right=3, top=2, bottom=3),
    ]

    pii_terms = ["one", "two"]

    matches = filter_to_pii(bounding_boxes=bounding_boxes, pii_terms=pii_terms)

    assert matches
    assert len(matches) == 2
    assert [m.text for m in matches] == pii_terms


def test_detect_text():
    # this image contains the word 'test' in it
    with open("tests/fixtures/test_image.png", "rb") as image_file:
        bounding_boxes = detect_text(BytesIO(image_file.read()))

    assert bounding_boxes
    assert len(bounding_boxes) == 1
    assert bounding_boxes[0].text == "test"


def test_detect_text_blank_image():
    # this is a blank image with no text
    with open("tests/fixtures/blank_image.png", "rb") as image_file:
        bounding_boxes = detect_text(BytesIO(image_file.read()))

    assert not bounding_boxes


def test_preprocess_text():
    text = "Sample text. With punctuation!"

    text = preprocess_text(text)

    assert text == "Sample text With punctuation"


def test_publish_to_exchange():
    channel = Mock()

    publish_to_exchange(
        channel=channel,
        correlation_id="123",
        body="test_message",
        routing_key="test_key",
    )

    properties = BasicProperties(correlation_id="123", delivery_mode=2)

    channel.basic_publish.assert_called_once_with(
        exchange="",
        routing_key="test_key",
        body="test_message",
        properties=properties,
    )


def test_upload_object_to_minio():
    mock_client = MagicMock(spec=Minio)

    mock_base_url = MagicMock()
    mock_base_url._url.geturl.return_value = "http://localhost:9000"
    mock_client._base_url = mock_base_url

    bucket_name = "test-bucket"
    path = "test/path"
    filename = "test_file.txt"
    obj_data = b"This is the content of the file."
    obj = BytesIO(obj_data)
    content_type = "text/plain"

    result = upload_object_to_minio(
        mock_client, bucket_name, path, filename, obj, content_type
    )

    mock_client.put_object.assert_called_once_with(
        bucket_name=bucket_name,
        object_name=os.path.join(path, filename),
        data=obj,
        content_type=content_type,
        length=len(obj_data),
    )

    expected_url = os.path.join(
        mock_client._base_url._url.geturl(), bucket_name, path, filename
    )
    assert result == expected_url
