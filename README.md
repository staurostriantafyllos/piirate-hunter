# Mimica Data/MLOps Engineer Challenge

This repository demonstrates a collection of microservices designed to function independently
in a real-world application. For simplicity and ease of development, all microservices
are currently housed within the same repository. They share common utilities, requirements
and a Dockerfile to streamline functionality and reduce code duplication.
While this structure aids in quick prototyping and testing, it is important to note that
in a real-world production environment these microservices would be separated into
distinct repositories, each with its own set of utilities, requirements and Dockerfile to
enhance modularity, scalability, and maintainability.

## Running

The microservices and other dependencies can be started with Docker Compose:

```bash
docker build -t pii:latest .

docker compose up -d
```

### Example

Use the following commands to run an example that submits and image and terms and gets the results.
After execution the script will save an image named output.png with the detected terms
redacted.

```bash
docker run --rm --network my_network -v "$(pwd):/app" myapp:latest python -m scripts.example

```
## Tests

Tests are run using pytest.

```bash
pytest tests/
```
