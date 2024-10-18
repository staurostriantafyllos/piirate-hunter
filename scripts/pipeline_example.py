from time import sleep

import requests
from PIL import Image, ImageDraw


def draw_bounding_boxes(image_path: str, bounding_boxes: list[dict]) -> None:
    """Draw bounding boxes around detected text on the image."""

    image = Image.open(image_path)
    draw = ImageDraw.Draw(image)

    for box in bounding_boxes:
        draw.rectangle(
            [box["left"], box["top"], box["right"], box["bottom"]],
            fill="black",
            outline="black",
            width=2,
        )

    image.save("images/output.png")


def main() -> None:
    api_url = "http://api:8000"
    image_path = "images/image.png"
    pii_terms = ["Alice", "Snowdrop"]

    with open(image_path, 'rb') as image_file:
        files = {'image': image_file}
        params = {'pii_terms': pii_terms}

        print(f"Sending request with terms: {pii_terms}")
        response = requests.post(url=f"{api_url}/pii", files=files, params=params)

    response.raise_for_status()
    correlation_id = response.json()["correlation_id"]

    matches = []

    while True:
        response = requests.get(url=f"{api_url}/pii/{correlation_id}")
        if response.status_code == 200:
            print("Results are ready:\n", response.json())
            matches = response.json()['matches']
            break
        sleep(0.5)

    draw_bounding_boxes(image_path=image_path, bounding_boxes=matches)


if __name__ == "__main__":
    main()
